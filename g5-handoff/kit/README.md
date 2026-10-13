# The Mac Pro handover kit

Everything on this machine, explained. All of these files are also installed at
`/usr/local/share/doc/macpro/kit/`.

## Read in this order

| If you are… | Read |
|---|---|
| **Just starting** | [QUICKSTART.md](QUICKSTART.md) — one page, five steps |
| Ready for a bit more | [NEW-OWNER-START-HERE.md](NEW-OWNER-START-HERE.md) — day one in detail |
| Wondering what is installed | [PROGRAMS-AND-APPS.md](PROGRAMS-AND-APPS.md) — every program and what it is for |
| Checking things over on day one | [FIRST-RUN-CHECKLIST.md](FIRST-RUN-CHECKLIST.md) |

## When something is wrong

| Problem | Read |
|---|---|
| **Black screen at start-up** | [LINUX-BOOT-AND-DISPLAY.md](LINUX-BOOT-AND-DISPLAY.md) — the one real gotcha on this machine |
| Worried about the disks | [DISK-HEALTH-AND-BACKUP.md](DISK-HEALTH-AND-BACKUP.md) — one drive is failing; read this |
| Something else | Run `ai check`, then `ai fix` |

## Going further

| | |
|---|---|
| The AI tools, and why each one exists | [AI-STACK.md](AI-STACK.md) |
| Signing up for accounts and API keys | [ACCOUNTS-AND-SIGN-IN.md](ACCOUNTS-AND-SIGN-IN.md) |
| Using Linux and the old Mac system together | [USING-BOTH-SYSTEMS.md](USING-BOTH-SYSTEMS.md) |
| Running the old Mac system as a virtual machine | [LION-VM.md](LION-VM.md) |
| **Writing and running Lion code from VS Code** | [LION-DEV-QUICKSTART.md](LION-DEV-QUICKSTART.md) — edit Lion's files in VS Code, run them in Lion, with AI |
| Day-to-day operating notes | [OPERATING-NOTES.md](OPERATING-NOTES.md) |
| Making the machine faster or newer | [HARDWARE-UPGRADE-PATH.md](HARDWARE-UPGRADE-PATH.md) |
| Things only a human can do | [HUMAN-STEPS.md](HUMAN-STEPS.md) |
| Disk partitioning, if you ever redo it | [PARTITION-RUNBOOK.md](PARTITION-RUNBOOK.md), [BOOT-STEPS.md](BOOT-STEPS.md) |
| The one page worth printing | [PRINT-THIS-FIRST.md](PRINT-THIS-FIRST.md) |

## Checking the documents are still true

```bash
validate-docs
```

That reads every document here and checks its factual claims against the running
machine: that each command exists, each port is listening, each path is present,
each link resolves. It exists because documentation drifts, and a beginner
cannot tell a stale instruction from a broken machine.

## One thing that must not be run

`kit/scrub/scrub.sh` erases the previous owner's personal files. **This machine
is going to the person who owns those files.** Do not run it. It is kept only
in case the machine is ever passed on to somebody else.
