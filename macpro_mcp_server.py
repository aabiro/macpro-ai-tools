"""MCP server for driving the Mac Pro 1,1 (Mac OS X 10.7 Lion) over SSH.

Beyond the four raw primitives, this exposes tools for the things that turned
out to be genuinely hard when doing real work on the machine remotely:

  * long jobs outliving the MCP request timeout        -> g5_run_detached / g5_job_status
  * installing an app without a sudo password          -> g5_install_app_from_pkg
  * proving a multi-gigabyte copy is not truncated     -> g5_verify_copy
  * knowing what needs root before wasting calls on it -> g5_privileges

Each of those encodes a mistake that cost real time. See the notes in
pixelenhance-labs/docs/g5-handoff/kit/OPERATING-NOTES.md, mirrored on the
machine at /Users/Shared/ai-cockpit/docs/OPERATING-NOTES.md.
"""

import base64
import shlex
import subprocess

try:
    # mcp >= 2.0: FastMCP was renamed MCPServer and moved
    from mcp.server.mcpserver import MCPServer
except ImportError:  # pragma: no cover - mcp 1.x fallback
    from mcp.server.fastmcp import FastMCP as MCPServer

mcp = MCPServer("MacPro G5 Controller")

SSH_TARGET = "macpro"
SSH_USER = "ai-cockpit"

# Lion's sshd is old enough that a modern client refuses its host key and
# signature algorithms unless asked. Without these you get
# "no matching host key type found. Their offer: ssh-rsa,ssh-dss", which looks
# like a failure but is only a policy mismatch.
SSH_OPTS = [
    "-o", f"User={SSH_USER}",
    "-o", "BatchMode=yes",
    "-o", "ConnectTimeout=15",
    "-o", "ServerAliveInterval=15",
    "-o", "ServerAliveCountMax=4",
    "-o", "HostKeyAlgorithms=+ssh-rsa",
    "-o", "PubkeyAcceptedAlgorithms=+ssh-rsa",
    "-o", "PubkeyAcceptedKeyTypes=+ssh-rsa",
]

MAX_OUTPUT_LENGTH = 15000
DEFAULT_TIMEOUT = 110  # stay inside the MCP request timeout
JOB_DIR = "/tmp/g5-jobs"
BLOCKED_DIRECTORIES = [
    ".venv", "venv", "node_modules", ".git", "__pycache__", "build", "dist",
]


def _clip(text: str, limit: int = MAX_OUTPUT_LENGTH) -> str:
    """Trim long output while keeping BOTH ends.

    The previous behaviour kept only the head, which is close to the worst
    choice: a command's verdict is almost always in its last lines, so the one
    part worth reading was the part discarded. Keep a generous head and a
    smaller tail, and say exactly how much went missing.
    """
    if len(text) <= limit:
        return text
    head = int(limit * 0.65)
    tail = limit - head
    dropped = len(text) - limit
    return (
        text[:head]
        + f"\n\n... [{dropped} characters elided from the middle] ...\n\n"
        + text[-tail:]
    )


def run_ssh_command(cmd: str, stdin_data: str = None, timeout: int = DEFAULT_TIMEOUT) -> str:
    """Run a command on the Mac over SSH and return its combined output.

    A non-zero exit status is reported but not treated as fatal: plenty of
    useful commands (grep with no match, pgrep, test) exit non-zero while
    still having said something worth reading. stderr is always included,
    because the interesting part of a macOS failure is usually there.
    """
    ssh_cmd = ["ssh"] + SSH_OPTS + [SSH_TARGET, cmd]
    try:
        # text=True means subprocess handles the encoding. Passing pre-encoded
        # bytes as `input` alongside it is a TypeError -- that was a live bug
        # in the previous version and it broke g5_write_file.
        result = subprocess.run(
            ssh_cmd,
            input=stdin_data if stdin_data is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return (
            f"TIMEOUT after {timeout}s. The command is likely still running on "
            f"the Mac.\nFor anything long, use g5_run_detached + g5_job_status "
            f"instead -- it survives this timeout."
        )
    except Exception as exc:  # noqa: BLE001
        return f"EXECUTION FAILED: {exc}"

    parts = []
    if result.stdout:
        parts.append(result.stdout)
    if result.stderr:
        parts.append(f"[stderr]\n{result.stderr}")
    if result.returncode != 0:
        parts.append(f"[exit code {result.returncode}]")
    return _clip("\n".join(parts)) if parts else "(no output)"


# ---------------------------------------------------------------------------
# Raw primitives
# ---------------------------------------------------------------------------


@mcp.tool()
def g5_execute_bash(command: str) -> str:
    """
    Execute a raw Bash command on the Mac Pro.
    Best for simple system queries, restarting services, or managing files.
    Output is truncated from the MIDDLE, keeping both the start and the end.

    For anything that may run longer than ~110 seconds (large copies, disk
    images, installs) use g5_run_detached instead -- this call will time out
    while the work continues orphaned.
    """
    return run_ssh_command(command)


@mcp.tool()
def g5_read_file(path: str) -> str:
    """
    Read the contents of a file on the Mac Pro.
    Blocks virtual environments, git directories and node_modules, and refuses
    files over 100 KB.
    """
    for blocked in BLOCKED_DIRECTORIES:
        if (
            f"/{blocked}/" in path
            or path.endswith(f"/{blocked}")
            or path.startswith(f"{blocked}/")
            or path == blocked
        ):
            return (
                f"ERROR: Access denied. Reading from '{blocked}' directories is "
                f"blocked to protect the context window."
            )

    quoted = shlex.quote(path)
    size_str = run_ssh_command(f"wc -c < {quoted} 2>/dev/null").strip()
    try:
        size = int(size_str.split()[0])
        if size > 100000:
            return (
                f"ERROR: File is too large ({size} bytes). Max allowed is "
                f"100,000. Use g5_execute_bash with head/tail/grep instead."
            )
    except (ValueError, IndexError):
        pass  # may not exist; let cat report it

    return run_ssh_command(f"cat {quoted}")


@mcp.tool()
def g5_write_file(path: str, content: str) -> str:
    """
    Write a file to the Mac Pro, base64-encoded in transit so Bash quoting,
    escaping and heredoc corruption cannot mangle it.
    """
    if isinstance(content, bytes):  # be forgiving about what we are handed
        content = content.decode("utf-8", "replace")
    b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")

    # shlex.quote the path so spaces and quotes in it cannot break out.
    remote = (
        "python -c 'import sys,base64;"
        "open(sys.argv[1],\"wb\").write(base64.b64decode(sys.stdin.read()))' "
        + shlex.quote(path)
    )
    result = run_ssh_command(remote, stdin_data=b64)
    if "FAILED" in result or "exit code" in result or "[stderr]" in result:
        return f"Write may have failed:\n{result}"
    return f"Successfully wrote {len(content)} bytes to {path}"


@mcp.tool()
def g5_run_python(script_content: str) -> str:
    """
    Execute a Python script on the Mac Pro using its native Python 2.7.
    Base64-encoded in transit, so no Bash quoting concerns.

    Remember the interpreter is 2.7.1: no f-strings, print is a statement,
    urllib2 rather than urllib.request, and standard library only -- the
    machine's TLS is too old to reach PyPI.
    """
    b64 = base64.b64encode(script_content.encode("utf-8")).decode("ascii")
    remote = 'python -c "import sys, base64; exec(base64.b64decode(sys.stdin.read()))"'
    return run_ssh_command(remote, stdin_data=b64)


# ---------------------------------------------------------------------------
# Long-running work
# ---------------------------------------------------------------------------


@mcp.tool()
def g5_run_detached(script: str, job_name: str) -> str:
    """
    Start a long-running Bash script on the Mac that OUTLIVES this request.

    Use for anything over ~110 seconds: multi-gigabyte copies, disk images,
    package extraction. Returns immediately; poll with g5_job_status(job_name).

    Handles three macOS-specific traps for you:
      * `setsid` does not exist on macOS -- uses nohup + disown instead.
      * Completion is signalled by an explicit marker in the log, never by
        process presence: `pgrep` is unreliable here and has reported a running
        job as finished, which once caused a 6 GB copy to be read while still
        being written (silently producing a 538 MB-short file).
      * stdin is detached from /dev/null so the job is not killed when the SSH
        session closes.
    """
    safe = "".join(c for c in job_name if c.isalnum() or c in "-_")
    if not safe:
        return "ERROR: job_name must contain at least one alphanumeric character."

    runner = f"{JOB_DIR}/{safe}.sh"
    log = f"{JOB_DIR}/{safe}.log"

    # The completion marker is written from an EXIT trap, not from a trailing
    # line. A trailing line is skipped by any `exit` inside the caller's script
    # -- and then g5_job_status reports RUNNING forever, which is exactly the
    # silent hang the marker exists to prevent. The trap fires on normal end,
    # early exit, and `set -e` abort alike.
    body = (
        "#!/bin/bash\n"
        f"exec > {shlex.quote(log)} 2>&1\n"
        f"trap 'rc=$?; echo \"### G5JOB DONE {safe} exit=$rc $(date)\"' EXIT\n"
        f"echo '### G5JOB START {safe}' \"$(date)\"\n"
        "set -o pipefail\n"
        f"{script}\n"
    )
    b64 = base64.b64encode(body.encode("utf-8")).decode("ascii")

    launch = (
        f"mkdir -p {JOB_DIR} && "
        f"python -c 'import sys,base64;"
        f"open(sys.argv[1],\"wb\").write(base64.b64decode(sys.stdin.read()))' "
        f"{shlex.quote(runner)} && "
        f"chmod +x {shlex.quote(runner)} && "
        f"( nohup {shlex.quote(runner)} >/dev/null 2>&1 </dev/null & disown ) && "
        f"echo launched"
    )
    result = run_ssh_command(launch, stdin_data=b64, timeout=45)
    if "launched" not in result:
        return f"Failed to launch job '{safe}':\n{result}"
    return (
        f"Job '{safe}' launched and detached.\n"
        f"  log: {log}\n"
        f"Poll it with: g5_job_status('{safe}')"
    )


@mcp.tool()
def g5_job_status(job_name: str, log_lines: int = 25) -> str:
    """
    Check a job started by g5_run_detached.

    Reports RUNNING / DONE / FAILED based on a marker written into the log, not
    on whether a process is visible -- process checks are unreliable on this
    machine and reporting a still-writing job as finished causes silent data
    corruption downstream.
    """
    safe = "".join(c for c in job_name if c.isalnum() or c in "-_")
    log = f"{JOB_DIR}/{safe}.log"
    q = shlex.quote(log)

    out = run_ssh_command(
        f"if [ ! -f {q} ]; then echo '__NOLOG__'; else "
        f"grep -c '### G5JOB DONE' {q} | tr -d ' '; echo '__SPLIT__'; "
        f"grep '### G5JOB DONE' {q} | tail -1; echo '__SPLIT__'; "
        f"tail -n {int(log_lines)} {q}; fi",
        timeout=45,
    )
    if "__NOLOG__" in out:
        return f"No log at {log}. Was the job launched? Check g5_run_detached output."

    chunks = out.split("__SPLIT__")
    done_count = chunks[0].strip().splitlines()[-1] if chunks[0].strip() else "0"
    done_line = chunks[1].strip() if len(chunks) > 1 else ""
    tail = chunks[2].strip() if len(chunks) > 2 else ""

    if done_count not in ("0", ""):
        status = "DONE"
        if "exit=0" not in done_line:
            status = f"FAILED ({done_line.split('exit=')[-1].split()[0] if 'exit=' in done_line else '?'})"
        return f"[{status}] {done_line}\n\n--- last {log_lines} lines ---\n{tail}"

    return f"[RUNNING] no completion marker yet\n\n--- last {log_lines} lines ---\n{tail}"


# ---------------------------------------------------------------------------
# Privilege-aware helpers
# ---------------------------------------------------------------------------


@mcp.tool()
def g5_privileges() -> str:
    """
    Report what this session can and cannot do, so calls are not wasted
    rediscovering it.

    Key fact: the account is in the `admin` group but sudo still demands a
    password, and there is no TTY here to supply one. That matters less than it
    looks -- admin group membership makes /Applications group-writable, so apps
    can be installed with no privileges at all (see g5_install_app_from_pkg).
    """
    return run_ssh_command(
        "echo '--- identity ---'; id -un; id -Gn; "
        "echo '--- console owner (GUI session belongs to them) ---'; "
        "stat -f '%Su' /dev/console; "
        "echo '--- passwordless sudo? ---'; "
        "sudo -n true 2>&1 | head -1 || true; "
        "echo '--- group-writable dirs we can install into ---'; "
        "for d in /Applications /Users/Shared /usr/local; do "
        "  if [ -d \"$d\" ]; then "
        "    if [ -w \"$d\" ]; then echo \"  WRITABLE  $d\"; "
        "    else echo \"  read-only $d\"; fi; "
        "  else echo \"  missing   $d\"; fi; done; "
        "echo '--- needs root (do not attempt; hand to the user) ---'; "
        "echo '  shutdown/halt, diskutil resizeVolume|appleRAID|verifyVolume,'; "
        "echo '  mdutil -i, pmset -a, bless --setBoot, installer -pkg'"
    )


@mcp.tool()
def g5_install_app_from_pkg(pkg_path: str, app_name: str = "") -> str:
    """
    Install a .app from an Apple flat .pkg WITHOUT sudo.

    `sudo installer -pkg ... -target /` is the documented route and needs a
    password this session cannot provide. It is also unnecessary: /Applications
    is drwxrwxr-x root:admin, so admin group membership alone is enough to place
    a bundle there. This extracts the payload with pkgutil/xar/cpio and installs
    it with ditto.

    Runs detached because payloads are often gigabytes. Poll the returned job
    with g5_job_status. Verify the result with g5_verify_copy if the bundle
    embeds a large disk image.
    """
    pkg = shlex.quote(pkg_path)
    script = f"""
WORK=/tmp/g5-pkg-$$
mkdir -p "$WORK" && cd "$WORK" || exit 1
echo "listing payload ..."
pkgutil --payload-files {pkg} 2>/dev/null | head -5
echo "extracting Payload with xar ..."
xar -xf {pkg} 2>/dev/null || {{ echo "xar failed"; exit 1; }}
PAYLOAD=$(find "$WORK" -name Payload | head -1)
[ -n "$PAYLOAD" ] || {{ echo "no Payload in pkg"; exit 1; }}
echo "payload: $PAYLOAD ($(stat -f %z "$PAYLOAD") bytes)"
mkdir -p "$WORK/out" && cd "$WORK/out" || exit 1
gunzip -c "$PAYLOAD" 2>/dev/null | cpio -idmu 2>&1 | tail -2 \
  || cpio -idmu < "$PAYLOAD" 2>&1 | tail -2
APP=$(find "$WORK/out" -maxdepth 2 -name "*.app" | head -1)
[ -n "$APP" ] || {{ echo "no .app found in payload"; exit 1; }}
echo "found: $APP"
DEST="/Applications/$(basename "$APP")"
rm -rf "$DEST"
ditto "$APP" "$DEST" || {{ echo "ditto failed"; exit 1; }}
echo "installed: $DEST ($(du -sh "$DEST" | cut -f1))"
echo "NOTE: if this pkg ships a separate InstallESD.dmg or large payload,"
echo "      it must be placed inside the bundle separately, then verified"
echo "      with g5_verify_copy."
rm -rf "$WORK/pkg" 2>/dev/null
"""
    job = "install-" + (app_name or "app").replace(" ", "-")[:24]
    return g5_run_detached(script, job)


@mcp.tool()
def g5_verify_copy(source_path: str, dest_path: str) -> str:
    """
    Prove a large file copied intact. Checks byte size AND, for disk images,
    the checksum type reported by hdiutil.

    Both checks matter. A 6 GB InstallESD.dmg copied while still being written
    landed 538 MB short and passed every casual inspection; what exposed it was
    the size mismatch plus hdiutil reporting `Format: UDRW, Checksum Type: none`
    where an intact compressed image reports CRC32.
    """
    s, d = shlex.quote(source_path), shlex.quote(dest_path)
    return run_ssh_command(
        f"A=$(stat -f %z {s} 2>/dev/null); B=$(stat -f %z {d} 2>/dev/null); "
        f'echo "source: ${{A:-missing}} bytes"; echo "dest  : ${{B:-missing}} bytes"; '
        f'if [ -n "$A" ] && [ "$A" = "$B" ]; then echo "SIZE MATCH"; '
        f'else echo "SIZE MISMATCH (diff $(( ${{A:-0}} - ${{B:-0}} )) bytes)"; fi; '
        f"case {d} in *.dmg) echo '--- dmg integrity ---'; "
        f"hdiutil imageinfo {d} 2>&1 | grep -iE 'Format:|Checksum Type' | head -3;; esac",
        timeout=100,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
