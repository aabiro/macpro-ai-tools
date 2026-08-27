# G5 MCP — driving this Mac Pro from another computer

`macpro_mcp_server.py` is an MCP server with **13 tools** that operate this Mac
Pro over SSH. It was written to build and repair the machine remotely, and it is
the reason a week of work could happen without sitting in front of it.

| Tool | What it does |
|---|---|
| `g5_execute_bash` | run a command |
| `g5_read_file` / `g5_write_file` | read and write files |
| `g5_run_python` | run a Python snippet |
| `g5_run_detached` / `g5_job_status` / `g5_job_progress` | start long jobs and poll them |
| `g5_privileges` | report what can be done without a password |
| `g5_install_app_from_pkg` | install a macOS `.pkg` without `sudo` |
| `g5_verify_copy` | size **and** structure check on a large copy |
| `g5_disk_layout` | full partition map |
| `g5_patch_bootloader` | install a 32-bit `boot.efi` |
| `g5_clone_volume` | clone a volume |

### Debian-side tools

The tools above drive Mac OS X. These three drive the Debian install on the
other disk. Only one of the two runs at a time, so each says so plainly when the
machine is booted into the other OS rather than returning an empty result that
reads as "nothing wrong".

| Tool | What it does |
|---|---|
| `g5_linux_boot_health` | kernel, command line, **initramfs sizes and dates**, recent boots, failed units |
| `g5_linux_desktop_exec` | run a command *inside the logged-in desktop session* |
| `g5_linux_screenshot` | capture the screen, copy it back, and check it is not blank |

They exist because of three specific failures during the repair of 2026-08-26,
and each encodes the lesson rather than describing it.

**`g5_linux_boot_health` returns numbers, never a verdict.** A DKMS driver
install silently rebuilt the initramfs to 85 MB, and this machine cannot boot an
image that size through its 32-bit EFI loader — it printed nothing at all, not
even with `earlyprintk` and `initcall_debug`. Three wrong causes were proposed
before anyone ran `ls -la /boot`, which showed it instantly. Healthy is ~20 MB;
anything near 70 MB is a boot failure waiting for the next restart.

**`g5_linux_desktop_exec` refuses to run without a display.** Resolving the
session by hand with `pgrep -f xfce4-session` matches the calling shell — whose
own command line contains that string — returning your PID, an empty `DISPLAY`,
and commands that silently do nothing while exiting 0. That produced three false
"fixed it" conclusions in one evening. This uses `pgrep -x`, which matches the
process name and cannot match the caller, and it aborts rather than run blind.

**`g5_linux_screenshot` proves you looked.** Services were checked over SSH and
reported as "everything is fine" while the display state was completely unknown.
It returns the image and reports the mean brightness and variation, because a
capture of a black screen and a failed capture are indistinguishable if you only
check that a file appeared.

> The connection uses `IdentitiesOnly=yes`, and that is not optional. Without
> it ssh offers every key in `~/.ssh` before the one named; each rejection logs
> `Failed publickey`, and `fail2ban` on this machine counts those as an attack.
> Automated use banned the administrator five times in one evening, and the
> symptom — port 22 refusing while every other service answered — was misread
> twice as sshd having failed. A refused connection means something sent a
> reset; suspect a ban before a dead daemon.

## Where it runs

**On your own computer, not on the Mac Pro.** It reaches the Mac over SSH:

```python
SSH_TARGET = "macpro"
SSH_USER   = "ai-cockpit"
```

Running it on the Mac Pro would mean SSHing to itself, and it targets the **Lion**
side specifically — so it only works while Lion is booted.

## Setup

1. Copy `macpro_mcp_server.py` to the machine you work from.
2. Add a `macpro` host to your `~/.ssh/config`:

   ```
   Host macpro
       HostName 192.168.1.124
       User ai-cockpit
       IdentityFile ~/.ssh/id_rsa
       PubkeyAcceptedAlgorithms +ssh-rsa
       HostKeyAlgorithms +ssh-rsa
   ```

   Those last two lines are not optional. Lion's sshd is old enough that a modern
   client refuses its host key outright — the error is *"no matching host key
   type found. Their offer: ssh-rsa,ssh-dss"*, which looks like a network fault
   and is not one.

3. Register it with your AI tool:

   ```bash
   claude mcp add g5 -s user -- python3 /path/to/macpro_mcp_server.py
   gemini mcp add -s user g5 python3 /path/to/macpro_mcp_server.py
   ```

## Why you may not need it

The Debian side now has its own read-only MCP servers — `macpro-health`,
`macpro-journal`, `macpro-apt` — which run **on** the machine and need no SSH.
For everyday questions ("is it healthy", "what did the last boot do") use those.

This one is for the harder case: driving the **Lion** side, or repairing the
machine when Debian will not boot.

**It is not read-only.** `g5_execute_bash` and `g5_write_file` do exactly what
they say. Unlike the `macpro-*` servers, this one can change things — which is
why it is documented separately and not registered by default.
