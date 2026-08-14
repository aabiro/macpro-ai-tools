import sys
import base64
import subprocess
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MacPro G5 Controller")

SSH_TARGET = "macpro"
SSH_USER = "ai-cockpit"

MAX_OUTPUT_LENGTH = 15000 # Truncate stdout if it gets too large
BLOCKED_DIRECTORIES = [".venv", "venv", "node_modules", ".git", "__pycache__", "build", "dist"]

def run_ssh_command(cmd: str, stdin_data: str = None) -> str:
    """Helper to run a raw SSH command."""
    ssh_cmd = ["ssh", "-o", f"User={SSH_USER}", SSH_TARGET, cmd]
    
    try:
        if stdin_data:
            result = subprocess.run(ssh_cmd, input=stdin_data.encode('utf-8'), capture_output=True, text=True, check=True)
        else:
            result = subprocess.run(ssh_cmd, capture_output=True, text=True, check=True)
            
        output = result.stdout
        if len(output) > MAX_OUTPUT_LENGTH:
            return output[:MAX_OUTPUT_LENGTH] + f"\n\n... [TRUNCATED: Output exceeded {MAX_OUTPUT_LENGTH} characters. Be more specific!]"
        return output
    except subprocess.CalledProcessError as e:
        err = f"ERROR (Exit Code {e.returncode}):\nSTDOUT:\n{e.stdout}\nSTDERR:\n{e.stderr}"
        if len(err) > MAX_OUTPUT_LENGTH:
            return err[:MAX_OUTPUT_LENGTH] + "\n\n... [TRUNCATED]"
        return err
    except Exception as e:
        return f"EXECUTION FAILED: {str(e)}"

@mcp.tool()
def g5_execute_bash(command: str) -> str:
    """
    Execute a raw Bash command on the Mac Pro.
    Best for simple system queries, restarting services, or managing files.
    Output is automatically truncated to prevent context window blowouts.
    """
    return run_ssh_command(command)

@mcp.tool()
def g5_read_file(path: str) -> str:
    """
    Read the contents of a file on the Mac Pro.
    Automatically blocks reading from virtual environments, git directories, or node_modules.
    """
    for blocked in BLOCKED_DIRECTORIES:
        if f"/{blocked}/" in path or path.endswith(f"/{blocked}") or path.startswith(f"{blocked}/") or path == blocked:
            return f"ERROR: Access denied. Reading from '{blocked}' directories is blocked to protect the context window."
            
    # Check file size before reading (prevent > 100KB)
    check_size_cmd = f"wc -c < '{path}'"
    size_str = run_ssh_command(check_size_cmd).strip()
    
    try:
        size = int(size_str)
        if size > 100000:
            return f"ERROR: File is too large ({size} bytes). Max allowed is 100,000 bytes. Use g5_execute_bash with 'head', 'tail', or 'grep' to search it instead."
    except ValueError:
        pass # File might not exist, let 'cat' handle the error
        
    return run_ssh_command(f"cat '{path}'")

@mcp.tool()
def g5_write_file(path: str, content: str) -> str:
    """
    Robustly write a file to the Mac Pro. 
    This tool base64 encodes the content locally and decodes it on the Mac Pro via Python,
    completely bypassing Bash quoting, escaping, and heredoc transfer corruption issues.
    """
    b64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    # We pipe the base64 string into python on the G5 to decode and write it safely
    remote_cmd = f'python -c "import sys, base64; open(\\"{path}\\", \\"wb\\").write(base64.b64decode(sys.stdin.read()))"'
    
    result = run_ssh_command(remote_cmd, stdin_data=b64_content)
    if "ERROR" in result or "FAILED" in result:
        return result
    return f"Successfully wrote {len(content)} bytes to {path}"

@mcp.tool()
def g5_run_python(script_content: str) -> str:
    """
    Robustly execute a Python script on the Mac Pro.
    This encodes the script to base64, sends it over SSH, and executes it in memory 
    using the G5's native Python 2.7 environment. Bypasses Bash quoting hell.
    """
    b64_script = base64.b64encode(script_content.encode('utf-8')).decode('utf-8')
    
    remote_cmd = 'python -c "import sys, base64; exec(base64.b64decode(sys.stdin.read()))"'
    
    return run_ssh_command(remote_cmd, stdin_data=b64_script)

if __name__ == "__main__":
    # Start the MCP server using standard input/output
    mcp.run(transport="stdio")
