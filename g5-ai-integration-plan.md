# Power Mac G5 AI Integration Master Plan

**Goal:** Transform the Power Mac G5 into an AI-augmented retro workstation by bypassing its legacy TLS/SSL limitations and building a suite of lightweight, era-appropriate client tools that leverage modern cloud LLMs.

**Context:** The G5 runs on the `xcelsior` Tailscale network. Modern LLM APIs (OpenAI, Anthropic, Google) require TLS 1.2/1.3, which the G5's outdated OpenSSL libraries cannot natively negotiate. The solution requires a modern gateway and lightweight retro clients.

---

## Phase 1: The Xcelsior AI Gateway (The Bridge)
**Objective:** Establish a secure proxy on a modern machine (MacBook) to handle modern TLS negotiation for the G5.

*   **Architecture:** A lightweight FastAPI (or Node.js/Express) server running on the modern MacBook.
*   **Ingress:** Binds to the MacBook's Tailscale IP (`100.64.0.3`) on a specific port (e.g., `8080`).
*   **Protocol:** Accepts plain HTTP POST requests from the G5 over the encrypted Tailscale mesh.
*   **Egress:** Translates the request, injects the necessary API keys, and makes the secure HTTPS call to the target LLM provider (Claude, OpenAI, Gemini).
*   **Deliverable:** A functional proxy script on the MacBook, and a test `curl` command proving the G5 can successfully receive an LLM response.

## Phase 2: "The Custodian" - Kernel Panic & Syslog Analyzer
**Objective:** Automate hardware and OS diagnosis using Gemini's large context window.

*   **Target Model:** Gemini 1.5 Pro (or Grok).
*   **Implementation (G5 Side):** A Bash/Python script (`g5-doctor`) that extracts recent critical entries from `/var/log/system.log` or `dmesg`.
*   **Workflow:**
    1. Script packages the logs.
    2. Sends them to the Xcelsior Gateway requesting the "Gemini/Grok Diagnostics" route.
    3. The Gateway prompts the LLM: *"You are an expert Apple technician diagnosing a PowerPC G5. Analyze these logs for hardware failures (RAM, PSU, thermal) or kernel panics."*
    4. G5 terminal displays the diagnosis.
*   **Deliverable:** `g5-doctor` CLI tool.

## Phase 3: "Retro-Coder" Translation Tool
**Objective:** Back-port modern code to compile on GCC 4.x and PowerPC architectures.

*   **Target Model:** Claude 3.5 Sonnet.
*   **Implementation (G5 Side):** A CLI tool (`retro-port <file>`).
*   **Workflow:**
    1. G5 script reads a source file.
    2. Sends the content to the Gateway requesting the "Claude Translation" route.
    3. Gateway prompts Claude: *"Rewrite this code to compile cleanly on GCC 4.0 for OS X 10.5 Leopard on a PowerPC 970. Use AltiVec intrinsics if applicable. Output only the raw code."*
    4. G5 script saves the returned code to `<file>_g5.c`.
*   **Deliverable:** `retro-port` CLI tool.

## Phase 4: "The Oracle" Full-Screen Terminal
**Objective:** A distraction-free, pure text interface for chatting with GPT-4o.

*   **Target Model:** ChatGPT (GPT-4o).
*   **Implementation (G5 Side):** A Python script using the `curses` library to create a clean, full-screen terminal UI.
*   **Workflow:**
    1. Renders a minimalist input prompt at the bottom of the screen.
    2. Sends user input to the Gateway's "Chat" route.
    3. Streams the response back into the UI.
    4. Maintains conversation history locally or relies on the Gateway to manage session state.
*   **Deliverable:** `oracle` interactive terminal application.

## Phase 5: Natural Language File Management
**Objective:** Use AI to generate safe, era-appropriate Bash commands.

*   **Target Model:** Claude 3.5 Sonnet or GPT-4o.
*   **Implementation (G5 Side):** A CLI wrapper (`g5-assist "prompt"`).
*   **Workflow:**
    1. Sends the user's intent to the Gateway.
    2. Gateway prompts the LLM: *"Translate this intent into a safe Bash command compatible with Bash 3.2 on OS X Leopard. Do not use modern flags. Output ONLY the command."*
    3. G5 script displays the proposed command.
    4. Prompts the user: `Execute this command? [y/N]`.
    5. If yes, executes via `os.system` or `subprocess`.
*   **Deliverable:** `g5-assist` CLI tool.

---

## Technical Considerations & Safeguards
*   **Editor Sync:** All development for these tools will happen on the MacBook using VS Code and the SFTP Sync extension, executing remotely on the G5 to prevent data loss.
*   **Security:** The Xcelsior Gateway must ONLY accept connections from the G5's Tailscale IP (`100.64.0.x`). API keys are stored securely on the MacBook, never on the G5.
*   **Dependencies:** G5 scripts must be written using built-in libraries available in Python 2.5/2.7 or native Bash to avoid complex dependency management on the retro OS.