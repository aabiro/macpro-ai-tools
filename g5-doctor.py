#!/usr/bin/env python
# The Custodian - G5 Kernel Panic & Syslog Analyzer
import os
import urllib2
import json
import sys

GATEWAY_URL = "http://100.64.0.6:8080/v1/chat/openai"
LOG_FILE = "/var/log/system.log"

def fetch_logs(lines=100):
    print("Reading the last %d lines of %s..." % (lines, LOG_FILE))
    try:
        # Use tail to efficiently grab the end of the log
        log_data = os.popen("tail -n %d %s" % (lines, LOG_FILE)).read()
        return log_data
    except Exception as e:
        return "Could not read logs: " + str(e)

def analyze_logs(log_data):
    print("Transmitting to modern node for AI analysis...")
    
    prompt = (
        "You are an expert Apple technician specializing in vintage PowerPC hardware (Power Mac G5) "
        "and early Intel Mac Pros running OS X Lion. Analyze the following system.log excerpt for any "
        "signs of hardware failure (RAM, PSU, thermal), kernel panics, or serious software errors. "
        "Give a concise, bulleted diagnosis.\n\n"
        "LOG DATA:\n" + log_data
    )
    
    data = json.dumps({
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 600
    })
    
    req = urllib2.Request(GATEWAY_URL, data, {'Content-Type': 'application/json'})
    try:
        response = urllib2.urlopen(req)
        result = json.loads(response.read())
        print("\n=== AI DIAGNOSTIC REPORT ===")
        print(result['choices'][0]['message']['content'])
        print("============================")
    except urllib2.HTTPError as e:
        print("HTTP Error:", e.code, e.read())
    except Exception as e:
        print("Error connecting to gateway:", e)

if __name__ == "__main__":
    # Check if a custom line count was provided
    lines = 100
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        lines = int(sys.argv[1])
        
    log_data = fetch_logs(lines)
    if log_data.strip():
        analyze_logs(log_data)
    else:
        print("No log data found or file is empty.")
