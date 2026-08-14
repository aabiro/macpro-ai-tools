#!/usr/bin/env python
# The Oracle - Full-screen terminal interface for ChatGPT on the Mac Pro G5
import curses
import urllib2
import json
import sys

GATEWAY_URL = "http://100.64.0.6:8080/v1/chat/openai"

def ask_gateway(prompt, history):
    messages = [{"role": "system", "content": "You are The Oracle, communicating through a 2004 Power Mac G5 terminal. Keep answers concise, intelligent, and slightly cyberpunk in tone."}]
    messages.extend(history)
    messages.append({"role": "user", "content": prompt})
    
    data = json.dumps({
        "model": "gpt-4o",
        "messages": messages,
        "max_tokens": 500
    })
    
    req = urllib2.Request(GATEWAY_URL, data, {'Content-Type': 'application/json'})
    try:
        response = urllib2.urlopen(req)
        result = json.loads(response.read())
        reply = result['choices'][0]['message']['content']
        return reply
    except Exception as e:
        return "ERROR: Connection to the modern world severed. " + str(e)

def main(stdscr):
    # Setup colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1) # Oracle text
    curses.init_pair(2, curses.COLOR_CYAN, -1)  # User text
    
    # Clear screen
    stdscr.clear()
    
    history = []
    
    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()
        
        # Draw header
        header = "=== THE ORACLE (POWERPC 970 LINK ACTIVE) ==="
        stdscr.addstr(0, (width - len(header)) // 2, header, curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(1, 0, "-" * width)
        
        # Draw history
        row = 2
        for msg in history[-10:]: # Show last few messages
            role = "USER:" if msg['role'] == 'user' else "ORACLE:"
            color = curses.color_pair(2) if msg['role'] == 'user' else curses.color_pair(1)
            
            # Simple text wrapping
            text = "%s %s" % (role, msg['content'])
            for i in range(0, len(text), width - 2):
                if row < height - 3:
                    stdscr.addstr(row, 0, text[i:i+width-2], color)
                    row += 1
        
        # Draw input prompt area
        stdscr.addstr(height - 2, 0, "-" * width)
        stdscr.addstr(height - 1, 0, "QUERY> ", curses.color_pair(2) | curses.A_BOLD)
        
        # Get input
        curses.echo()
        stdscr.refresh()
        prompt = stdscr.getstr(height - 1, 7, width - 8)
        curses.noecho()
        
        if prompt.lower() in ['exit', 'quit', 'q']:
            break
            
        if prompt.strip() == "":
            continue
            
        stdscr.addstr(height - 1, 7, "Transmitting to modern node...", curses.A_DIM)
        stdscr.refresh()
        
        # Fetch response
        response = ask_gateway(prompt, history)
        
        # Update history
        history.append({"role": "user", "content": prompt})
        history.append({"role": "assistant", "content": response})

if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        sys.exit(0)
