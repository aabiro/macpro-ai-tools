#!/usr/bin/env python
# The G5 AI Cockpit - Unified Terminal Interface
import curses
import urllib2
import json
import sys
import os
import textwrap

GATEWAY_URL = "http://100.64.0.6:8080/v1/chat"
LOG_FILE = "/var/log/system.log"

def call_gateway(provider, prompt, system_prompt=None, history=None):
    if history is None:
        history = []
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    
    data = json.dumps({
        "model": "gpt-4o" if provider == "openai" else "claude-3-5-sonnet-20240620",
        "messages": messages,
        "max_tokens": 800
    })
    
    url = "%s/%s" % (GATEWAY_URL, provider)
    req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
    try:
        response = urllib2.urlopen(req)
        result = json.loads(response.read())
        # Handle both OpenAI and Anthropic response formats roughly
        if provider == "openai":
            return result['choices'][0]['message']['content']
        else:
            return result.get('content', [{'text': 'No response text'}])[0].get('text', str(result))
    except Exception as e:
        return "LINK SEVERED: " + str(e)

def fetch_logs(lines=100):
    try:
        # Requires the user to have sudo NOPASSWD access to tail /var/log/system.log
        return os.popen("sudo tail -n %d %s" % (lines, LOG_FILE)).read()
    except Exception as e:
        return "Log access denied: " + str(e)

def draw_header(stdscr, width, active_mode):
    header = " === G5 AI COCKPIT [LINK: 100.64.0.6] === "
    stdscr.addstr(0, (width - len(header)) // 2, header, curses.color_pair(3) | curses.A_BOLD | curses.A_REVERSE)
    
    modes = [("1", "Oracle"), ("2", "Custodian (Logs)"), ("3", "Retro-Coder"), ("Q", "Quit")]
    mode_str = " | ".join("[%s] %s" % (k, n) for k, n in modes)
    stdscr.addstr(1, 2, mode_str, curses.color_pair(4))
    stdscr.addstr(2, 0, "=" * width, curses.color_pair(3))

def main(stdscr):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)   # AI Text
    curses.init_pair(2, curses.COLOR_CYAN, -1)    # User Text
    curses.init_pair(3, curses.COLOR_MAGENTA, -1) # Borders/Headers
    curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Status
    curses.init_pair(5, curses.COLOR_RED, -1)     # Errors

    mode = "oracle"
    oracle_history = []
    sys_log_result = ""
    
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        draw_header(stdscr, width, mode)
        
        if mode == "oracle":
            row = 4
            for msg in oracle_history[-10:]:
                role = "USER:" if msg['role'] == 'user' else "ORACLE:"
                color = curses.color_pair(2) if msg['role'] == 'user' else curses.color_pair(1)
                
                wrapped = textwrap.wrap("%s %s" % (role, msg['content']), width - 4)
                for line in wrapped:
                    if row < height - 3:
                        stdscr.addstr(row, 2, line, color)
                        row += 1
            
            stdscr.addstr(height - 2, 0, "-" * width, curses.color_pair(3))
            stdscr.addstr(height - 1, 2, "QUERY> ", curses.color_pair(2) | curses.A_BOLD)
            
            curses.echo()
            stdscr.refresh()
            user_input = stdscr.getstr(height - 1, 9, width - 10)
            curses.noecho()
            
            if user_input.lower() in ['1', '2', '3', 'q', 'quit']:
                cmd = user_input.lower()
                if cmd in ['q', 'quit']: break
                elif cmd == '2': mode = "custodian"; continue
                elif cmd == '3': mode = "coder"; continue
            
            if user_input.strip() == "": continue
            
            stdscr.addstr(height - 1, 9, "Transmitting...", curses.A_DIM)
            stdscr.refresh()
            
            sys_prompt = "You are The Oracle, communicating through a 2004 Power Mac G5 terminal. Keep answers concise and slightly cyberpunk."
            reply = call_gateway("openai", user_input, sys_prompt, oracle_history)
            oracle_history.append({"role": "user", "content": user_input})
            oracle_history.append({"role": "assistant", "content": reply})
            
        elif mode == "custodian":
            stdscr.addstr(4, 2, "CUSTODIAN ACTIVE: Analyzing /var/log/system.log", curses.color_pair(4) | curses.A_BOLD)
            if not sys_log_result:
                stdscr.addstr(6, 2, "Fetching logs and querying mainframe...", curses.A_DIM)
                stdscr.refresh()
                logs = fetch_logs(100)
                sys_prompt = "You are a vintage Apple technician diagnosing a PowerPC G5. Analyze the following OS X system.log excerpt for hardware/software faults. Be concise."
                sys_log_result = call_gateway("openai", logs, sys_prompt)
            
            row = 6
            wrapped = textwrap.wrap(sys_log_result, width - 4)
            for line in wrapped:
                if row < height - 3:
                    stdscr.addstr(row, 2, line, curses.color_pair(1))
                    row += 1
                    
            stdscr.addstr(height - 2, 0, "-" * width, curses.color_pair(3))
            stdscr.addstr(height - 1, 2, "Press [1] for Oracle, [R] to re-scan, or [Q] to quit.", curses.color_pair(4))
            
            key = stdscr.getch()
            if key in [ord('q'), ord('Q')]: break
            elif key in [ord('1')]: mode = "oracle"
            elif key in [ord('r'), ord('R')]: sys_log_result = ""
            
        elif mode == "coder":
            stdscr.addstr(4, 2, "RETRO-CODER: Not yet implemented in Cockpit v1.0", curses.color_pair(5) | curses.A_BOLD)
            stdscr.addstr(height - 1, 2, "Press [1] to return to Oracle.", curses.color_pair(4))
            key = stdscr.getch()
            if key in [ord('1')]: mode = "oracle"
            elif key in [ord('q'), ord('Q')]: break

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
