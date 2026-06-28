import sys
import subprocess
import time
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# --- ARGUMENT PARSING ---
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
AUTO_STOP_SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 14400 
MC_COMMAND = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else "java -Xmx2G -jar server.jar nogui"

mc_process = None
shutdown_timer = None
start_time = None
httpd = None  # Reference to the web server instance

HTML_PAGE = """<!DOCTYPE html>
<html>
<head>
    <title>MC Controller</title>
    <style>
        body {{ font-family: sans-serif; text-align: center; margin-top: 50px; background: #222; color: #fff; }}
        button {{ font-size: 18px; padding: 10px 20px; margin: 10px; cursor: pointer; border-radius: 5px; border: none; }}
        .start {{ background: #28a745; color: white; }}
        .stop {{ background: #dc3545; color: white; }}
        .restart {{ background: #ffc107; color: black; }}
        .status {{ font-weight: bold; color: #17a2b8; }}
        .cmd {{ font-family: monospace; background: #111; padding: 8px; color: #00ff00; display: inline-block; }}
    </style>
</head>
<body>
    <h1>Minecraft Server Control Panel</h1>
    <p>Status: <span class="status">{status}</span></p>
    <p>Time Remaining: <span style="color: #ffc107; font-weight: bold;">{time_left}</span></p>
    <p>Command: <span class="cmd">{cmd}</span></p>
    <hr>
    <button class="start" onclick="location.href='/start'">Start</button>
    <button class="stop" onclick="location.href='/stop'">Stop</button>
    <button class="restart" onclick="location.href='/restart'">Restart</button>
</body>
</html>
"""

def auto_stop_trigger():
    print(f"[!] Auto-shutdown limit reached ({AUTO_STOP_SECS}s). Stopping Minecraft...")
    manage_server("stop")

def manage_server(action):
    global mc_process, shutdown_timer, start_time, httpd
    is_running = mc_process and mc_process.poll() is None

    if action == "start" and not is_running:
        print(f"[+] Launching Minecraft...")
        start_time = time.time()
        mc_process = subprocess.Popen(
            MC_COMMAND, 
            shell=True, 
            stdin=subprocess.PIPE, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True
        )
        shutdown_timer = threading.Timer(AUTO_STOP_SECS, auto_stop_trigger)
        shutdown_timer.start()

    elif action == "stop" and is_running:
        if shutdown_timer:
            shutdown_timer.cancel()
            shutdown_timer = None
        
        print("[+] Stopping Minecraft server gracefully...")
        try:
            mc_process.communicate(input="stop\n", timeout=20)
        except:
            mc_process.kill()
        
        mc_process = None
        start_time = None
        
        # KILL THE WEB SERVER LOOP SO GITHUB ACTIONS COMPLETES
        print("[+] Shutting down Python controller...")
        if httpd:
            threading.Thread(target=httpd.shutdown).start()

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global mc_process, start_time
        if self.path in ["/start", "/stop", "/restart"]:
            action = self.path[1:]
            if action == "restart":
                manage_server("stop")
                time.sleep(2)
                manage_server("start")
            else:
                manage_server(action)
            self.send_response(303)
            self.send_header("Location", "/")
            self.end_headers()
            return

        is_running = mc_process and mc_process.poll() is None
        status = "RUNNING" if is_running else "STOPPED"
        
        if is_running and start_time:
            elapsed = time.time() - start_time
            remaining = max(0, int(AUTO_STOP_SECS - elapsed))
            mins, secs = divmod(remaining, 60)
            hrs, mins = divmod(mins, 60)
            time_left_str = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        else:
            time_left_str = "N/A"

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_PAGE.format(status=status, cmd=MC_COMMAND, time_left=time_left_str).encode())

    def log_message(self, format, *args): return

if __name__ == "__main__":
    print(f"Control Panel: http://localhost:{PORT}")
    httpd = HTTPServer(("", PORT), SimpleHandler)
    
    # Auto-start the server immediately when the script runs in GitHub Actions
    manage_server("start")
    
    # This keeps the workflow step active until httpd.shutdown() is called
    httpd.serve_forever()