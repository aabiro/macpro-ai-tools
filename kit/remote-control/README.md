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
