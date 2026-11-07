"""Offline tests for every tool in macpro_mcp_server.py.

Nothing here reaches the Mac Pro. subprocess.run is replaced by a fake that
records the ssh command line and answers with canned output, which checks the
two places bugs have hidden: what each tool SENDS, and how it READS the reply.
For a live run against the real machine use
g5-handoff/kit/remote-control/test-mcp-remote.py.

    .venv/bin/python -m unittest discover -s tests -v
"""

import asyncio
import base64
import importlib.util
import os
import subprocess
import tempfile
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVER = os.path.join(ROOT, "macpro_mcp_server.py")
KIT_SERVER = os.path.join(
    ROOT, "g5-handoff", "kit", "remote-control", "macpro_mcp_server.py")


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


srv = load(SERVER, "macpro_mcp_server")

# (readOnlyHint, destructiveHint, idempotentHint, openWorldHint) per tool: the
# contract a client sees before it decides whether to warn the user.
EXPECTED_HINTS = {
    "g5_execute_bash":         (False, True,  False, True),
    "g5_read_file":            (True,  False, True,  False),
    "g5_write_file":           (False, True,  True,  False),
    "g5_run_python":           (False, True,  False, True),
    "g5_run_detached":         (False, True,  False, True),
    "g5_job_status":           (True,  False, True,  False),
    "g5_job_progress":         (True,  False, True,  False),
    "g5_privileges":           (True,  False, True,  False),
    "g5_install_app_from_pkg": (False, True,  False, False),
    "g5_verify_copy":          (True,  False, True,  False),
    "g5_disk_layout":          (True,  False, True,  False),
    "g5_patch_bootloader":     (False, True,  True,  False),
    "g5_clone_volume":         (False, True,  False, False),
    "g5_linux_boot_health":    (True,  False, True,  False),
    "g5_linux_desktop_exec":   (False, True,  False, True),
    "g5_linux_screenshot":     (False, False, False, False),
    "g5_lion_vm_control":      (False, False, True,  False),
    "g5_lion_exec":            (False, True,  False, True),
}


class FakeRun:
    """Stands in for subprocess.run. Records every call; replies with `reply`.

    `reply` is a CompletedProcess field dict, or a callable taking argv and
    returning one, for tools that make more than one call.
    """

    def __init__(self, stdout="", stderr="", returncode=0, reply=None):
        self.calls = []
        self.reply = reply or (lambda argv: {
            "stdout": stdout, "stderr": stderr, "returncode": returncode})

    def __call__(self, argv, input=None, **kwargs):
        self.calls.append({"argv": argv, "input": input})
        r = self.reply(argv)
        return subprocess.CompletedProcess(
            argv, r.get("returncode", 0), r.get("stdout", ""), r.get("stderr", ""))

    @property
    def remote(self):
        """The command string the last call asked the far side to run."""
        return self.calls[-1]["argv"][-1]

    @property
    def stdin(self):
        return self.calls[-1]["input"]


class ToolTest(unittest.TestCase):
    def fake(self, **kwargs):
        run = FakeRun(**kwargs)
        patcher = mock.patch.object(srv.subprocess, "run", run)
        patcher.start()
        self.addCleanup(patcher.stop)
        return run


class AdvertisedTools(unittest.TestCase):
    def setUp(self):
        self.tools = {t.name: t for t in asyncio.run(srv.mcp.list_tools())}

    def test_advertises_exactly_the_expected_tools(self):
        self.assertEqual(set(self.tools), set(EXPECTED_HINTS))

    def test_every_tool_declares_all_four_hints(self):
        for name, expected in EXPECTED_HINTS.items():
            with self.subTest(tool=name):
                a = self.tools[name].annotations
                self.assertIsNotNone(a, "no annotations")
                got = (a.read_only_hint, a.destructive_hint,
                       a.idempotent_hint, a.open_world_hint)
                for hint in got:
                    self.assertIsInstance(hint, bool)
                self.assertEqual(got, expected)
                self.assertTrue(a.title)

    def test_hints_serialise_under_their_protocol_names(self):
        wire = self.tools["g5_read_file"].annotations.model_dump(by_alias=True)
        for key in ("readOnlyHint", "destructiveHint",
                    "idempotentHint", "openWorldHint"):
            self.assertIn(key, wire)

    def test_read_only_tools_are_never_destructive(self):
        for name, t in self.tools.items():
            if t.annotations.read_only_hint:
                self.assertFalse(t.annotations.destructive_hint, name)

    def test_handover_kit_copy_is_identical(self):
        with open(SERVER, "rb") as a, open(KIT_SERVER, "rb") as b:
            self.assertEqual(a.read(), b.read(),
                             "copy macpro_mcp_server.py into the kit")


class RawPrimitives(ToolTest):
    def test_g5_execute_bash_returns_output(self):
        run = self.fake(stdout="Darwin\n")
        self.assertEqual(srv.g5_execute_bash("uname"), "Darwin\n")
        self.assertTrue(run.remote.startswith("export LC_ALL=C LANG=C; "))
        self.assertTrue(run.remote.endswith("uname"))
        self.assertIn("HostKeyAlgorithms=+ssh-rsa", run.calls[0]["argv"])

    def test_g5_execute_bash_reports_stderr_and_exit_code(self):
        self.fake(stdout="", stderr="no such file", returncode=1)
        out = srv.g5_execute_bash("ls /nope")
        self.assertIn("[stderr]\nno such file", out)
        self.assertIn("[exit code 1]", out)

    def test_g5_execute_bash_keeps_both_ends_of_long_output(self):
        self.fake(stdout="HEAD" + "x" * 50000 + "TAIL")
        out = srv.g5_execute_bash("big")
        self.assertTrue(out.startswith("HEAD"))
        self.assertTrue(out.endswith("TAIL"))
        self.assertIn("elided from the middle", out)

    def test_g5_execute_bash_timeout_points_at_detached_jobs(self):
        def boom(*a, **k):
            raise subprocess.TimeoutExpired("ssh", 110)
        with mock.patch.object(srv.subprocess, "run", boom):
            out = srv.g5_execute_bash("sleep 999")
        self.assertIn("TIMEOUT", out)
        self.assertIn("g5_run_detached", out)

    def test_g5_read_file_blocks_heavy_directories(self):
        run = self.fake()
        for path in ("/a/node_modules/x.js", "proj/.venv", ".git/config"):
            self.assertIn("Access denied", srv.g5_read_file(path))
        self.assertEqual(run.calls, [])

    def test_g5_read_file_refuses_files_over_100kb(self):
        self.fake(stdout="250000\n")
        self.assertIn("too large", srv.g5_read_file("/var/log/system.log"))

    def test_g5_read_file_quotes_the_path(self):
        run = self.fake(stdout="12\n")
        srv.g5_read_file("/Users/Shared/it's here.txt")
        self.assertIn("cat '/Users/Shared/it'\"'\"'s here.txt'", run.remote)

    def test_g5_write_file_sends_content_base64_on_stdin(self):
        run = self.fake()
        content = "line 'one'\n$HOME `two` \"three\"\n"
        out = srv.g5_write_file("/tmp/a b.txt", content)
        self.assertEqual(base64.b64decode(run.stdin).decode(), content)
        self.assertIn("'/tmp/a b.txt'", run.remote)
        self.assertNotIn("HOME", run.remote)
        self.assertIn("Successfully wrote", out)

    def test_g5_write_file_reports_a_failed_write(self):
        self.fake(stderr="Permission denied", returncode=1)
        self.assertIn("may have failed", srv.g5_write_file("/etc/x", "y"))

    def test_g5_run_python_sends_script_base64_on_stdin(self):
        run = self.fake(stdout="2.7.1\n")
        script = "import sys\nprint sys.version\n"
        self.assertEqual(srv.g5_run_python(script), "2.7.1\n")
        self.assertEqual(base64.b64decode(run.stdin).decode(), script)
        self.assertNotIn("print", run.remote)


class LongJobs(ToolTest):
    def test_g5_run_detached_writes_an_exit_trap_and_detaches(self):
        run = self.fake(stdout="launched\n")
        out = srv.g5_run_detached("cp big /Volumes/x", "copy; rm -rf /")
        body = base64.b64decode(run.stdin).decode()
        self.assertIn("trap '", body)
        self.assertIn("### G5JOB DONE copyrm-rf", body)
        self.assertIn("cp big /Volumes/x", body)
        self.assertIn("nohup", run.remote)
        self.assertNotIn(";rm", run.remote)
        self.assertIn("launched and detached", out)

    def test_g5_run_detached_rejects_a_name_with_nothing_safe_in_it(self):
        run = self.fake()
        self.assertIn("ERROR", srv.g5_run_detached("true", "!!!"))
        self.assertEqual(run.calls, [])

    def test_g5_run_detached_reports_a_failed_launch(self):
        self.fake(stderr="No space left on device", returncode=1)
        self.assertIn("Failed to launch", srv.g5_run_detached("true", "j"))

    def test_g5_job_status_done(self):
        self.fake(stdout="1\n__SPLIT__\n### G5JOB DONE j exit=0 Tue\n"
                         "__SPLIT__\nall copied\n")
        out = srv.g5_job_status("j")
        self.assertTrue(out.startswith("[DONE]"))
        self.assertIn("all copied", out)

    def test_g5_job_status_failed_shows_exit_code(self):
        self.fake(stdout="1\n__SPLIT__\n### G5JOB DONE j exit=2 Tue\n"
                         "__SPLIT__\nboom\n")
        self.assertTrue(srv.g5_job_status("j").startswith("[FAILED (2)]"))

    def test_g5_job_status_running_without_a_marker(self):
        self.fake(stdout="0\n__SPLIT__\n\n__SPLIT__\nstill going\n")
        self.assertTrue(srv.g5_job_status("j").startswith("[RUNNING]"))

    def test_g5_job_status_without_a_log(self):
        self.fake(stdout="__NOLOG__\n")
        self.assertIn("No log at /tmp/g5-jobs/j.log", srv.g5_job_status("j"))

    def test_g5_job_progress_uses_ps_not_pgrep(self):
        run = self.fake(stdout="no ditto process running\n")
        srv.g5_job_progress("ditto", job_name="clone")
        self.assertNotIn("pgrep", run.remote)
        self.assertIn("ps -axo pid,comm", run.remote)
        self.assertIn("/tmp/g5-jobs/clone.log", run.remote)


class Administration(ToolTest):
    def test_g5_privileges_asks_sudo_without_prompting(self):
        run = self.fake(stdout="ai-cockpit\n")
        srv.g5_privileges()
        self.assertIn("sudo -n true", run.remote)

    def test_g5_install_app_from_pkg_runs_detached_without_sudo(self):
        run = self.fake(stdout="launched\n")
        out = srv.g5_install_app_from_pkg("/Users/Shared/Install Lion.pkg",
                                          "Install Lion")
        body = base64.b64decode(run.stdin).decode()
        self.assertIn("'/Users/Shared/Install Lion.pkg'", body)
        self.assertIn("ditto", body)
        self.assertNotIn("sudo", body)
        self.assertIn("install-Install-Lion", out)

    def test_g5_verify_copy_checks_size_and_dmg_checksum(self):
        run = self.fake(stdout="SIZE MATCH\n")
        srv.g5_verify_copy("/a/InstallESD.dmg", "/b/Install ESD.dmg")
        self.assertIn("'/b/Install ESD.dmg'", run.remote)
        self.assertIn("hdiutil imageinfo", run.remote)

    def test_g5_disk_layout_calls_diskutil_list_bare(self):
        run = self.fake(stdout="/dev/disk0\n")
        srv.g5_disk_layout()
        # Lion's diskutil list with two devices returns nothing at all.
        self.assertIn("diskutil list 2>/dev/null", run.remote)

    def test_g5_patch_bootloader_patches_both_locations(self):
        run = self.fake(stdout="RESULT: both locations carry the patch\n")
        srv.g5_patch_bootloader("/Volumes/Lion/", "/tmp/boot.efi", "abc123")
        self.assertIn("V=/Volumes/Lion;", run.remote)
        self.assertIn("System/Library/CoreServices/boot.efi", run.remote)
        self.assertIn("usr/standalone/i386/boot.efi", run.remote)
        self.assertIn("chflags nouchg", run.remote)
        self.assertIn("EXP=abc123", run.remote)

    def test_g5_clone_volume_uses_ditto_x_and_reblesses(self):
        run = self.fake(stdout="launched\n")
        out = srv.g5_clone_volume("/", "/Volumes/Backup HD", "clone")
        body = base64.b64decode(run.stdin).decode()
        self.assertIn("ditto -X", body)
        self.assertIn("DST='/Volumes/Backup HD'", body)
        self.assertIn("bless --folder", body)
        self.assertIn("'clone' launched", out)


class DebianSide(ToolTest):
    def test_g5_linux_boot_health_uses_the_named_key_only(self):
        run = self.fake(stdout="6.12.0\n")
        srv.g5_linux_boot_health()
        argv = run.calls[0]["argv"]
        self.assertIn("IdentitiesOnly=yes", argv)
        self.assertIn(srv.LINUX_KEY, argv)
        self.assertIn(srv.LINUX_TARGET, argv)
        self.assertIn("/boot/initrd.img-*", run.remote)

    def test_g5_linux_boot_health_says_when_lion_is_booted(self):
        self.fake(stderr="ssh: connect to host %s port 22: Connection refused"
                         % srv.LINUX_HOST, returncode=255)
        self.assertIn("Debian is not answering", srv.g5_linux_boot_health())

    def test_g5_linux_boot_health_says_when_the_machine_is_off(self):
        self.fake(stderr="ssh: connect to host %s port 22: No route to host"
                         % srv.LINUX_HOST, returncode=255)
        self.assertIn("not reachable at all", srv.g5_linux_boot_health())

    def test_g5_linux_desktop_exec_resolves_session_by_exact_name(self):
        run = self.fake(stdout="[session pid 900, DISPLAY=:0]\n[exit 0]\n")
        srv.g5_linux_desktop_exec("notify-send 'hi there'")
        self.assertIn("pgrep -x xfce4-session", run.remote)
        self.assertNotIn("pgrep -f", run.remote)
        self.assertIn("sh -c 'notify-send '\"'\"'hi there'\"'\"''", run.remote)

    def test_g5_linux_screenshot_stops_when_capture_is_refused(self):
        run = self.fake(stdout="REFUSED: no desktop session\n", returncode=1)
        self.assertIn("Capture failed", srv.g5_linux_screenshot("/tmp"))
        self.assertEqual(len(run.calls), 1)

    def test_g5_linux_screenshot_copies_the_image_back(self):
        with tempfile.TemporaryDirectory() as tmp:
            def reply(argv):
                if argv[0] == "scp":
                    with open(argv[-1], "wb") as f:
                        f.write(b"\x89PNG fake")
                    return {}
                return {"stdout": "CAPTURED\n123 bytes\n"}
            run = self.fake(reply=reply)
            out = srv.g5_linux_screenshot(tmp)
            self.assertEqual([c["argv"][0] for c in run.calls], ["ssh", "scp"])
            self.assertIn("saved: " + os.path.join(tmp, "g5-shot.png"), out)

    def test_g5_lion_vm_control_maps_each_action(self):
        expected = {
            "status": "lion-vm status",
            "start": "lion-vm start && lion-vm wait",
            "stop": "lion-vm stop",
            "screenshot": "lion-vm screenshot /tmp/lion-shot.png",
        }
        for action, command in expected.items():
            with self.subTest(action=action):
                run = self.fake(stdout="ok\n")
                srv.g5_lion_vm_control(action.upper())
                self.assertEqual(run.remote, command)

    def test_g5_lion_vm_control_rejects_unknown_actions(self):
        run = self.fake()
        self.assertIn("Unknown action", srv.g5_lion_vm_control("reboot"))
        self.assertEqual(run.calls, [])

    def test_g5_lion_exec_quotes_the_command_for_the_guest(self):
        run = self.fake(stdout="10.7.5\n")
        self.assertEqual(srv.g5_lion_exec("echo 'hi'"), "10.7.5")
        self.assertEqual(run.remote, "lion 'echo '\\''hi'\\'''")

    def test_g5_lion_exec_says_how_to_start_a_stopped_vm(self):
        # Debian answered; it is `lion`'s own ssh to the VM that was refused.
        self.fake(stderr="ssh: connect to host 127.0.0.1 port 2222: "
                         "Connection refused", returncode=255)
        out = srv.g5_lion_exec("true")
        self.assertIn('g5_lion_vm_control("start")', out)
        self.assertNotIn("Debian is not answering", out)

    def test_g5_lion_exec_ignores_an_empty_command(self):
        run = self.fake()
        self.assertEqual(srv.g5_lion_exec("  "), "No command given.")
        self.assertEqual(run.calls, [])


if __name__ == "__main__":
    unittest.main()
