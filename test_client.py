#!/usr/bin/env python
# Run this on the Mac Pro!
import urllib2
import json

# Replace with your MacBook's Tailscale IP if different
GATEWAY_URL = "http://100.64.0.6:8080/v1/chat/openai"

def ask_oracle(prompt):
    print("Asking the Oracle: '%s'..." % prompt)
    
    # We use urllib2 because it's built into older Python 2.x versions 
    # that are likely native on OS X Lion
    data = json.dumps({
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 100
    })
    
    req = urllib2.Request(GATEWAY_URL, data, {'Content-Type': 'application/json'})
    
    try:
        response = urllib2.urlopen(req)
        result = json.loads(response.read())
        print("\nOracle says:")
        print("-------------------")
        print(result['choices'][0]['message']['content'])
        print("-------------------")
    except urllib2.HTTPError as e:
        print("HTTP Error:", e.code, e.read())
    except urllib2.URLError as e:
        print("URL Error:", e.reason)
        print("Make sure the Gateway is running on the MacBook!")

if __name__ == "__main__":
    ask_oracle("You are talking to a Power Mac G5. Say hello in a retro, cyberpunk style!")
