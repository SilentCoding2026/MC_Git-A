import http.server
import socketserver
import urllib.parse
import urllib.request
import os
import threading

PORT = 8080

HTML_FORM = """<!DOCTYPE html>
<html>
<head>
    <title>VPS Remote Downloader</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; line-height: 1.6; }}
        .form-group {{ margin-bottom: 15px; }}
        label {{ display: block; font-weight: bold; margin-bottom: 5px; }}
        input[type="text"] {{ width: 100%; padding: 8px; box-sizing: border-box; }}
        .btn {{ color: white; padding: 10px 15px; border: none; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; border-radius: 4px; }}
        .btn-primary {{ background-color: #007BFF; }}
        .btn-primary:hover {{ background-color: #0056b3; }}
        .btn-danger {{ background-color: #DC3545; }}
        .btn-danger:hover {{ background-color: #bd2130; }}
        .message {{ padding: 10px; margin-top: 20px; border-radius: 4px; }}
        .success {{ background-color: #d4edda; color: #155724; }}
        .error {{ background-color: #f8d7da; color: #721c24; }}
        .actions {{ margin-top: 20px; display: flex; gap: 10px; }}
    </style>
</head>
<body>
    <h2>VPS Remote Downloader</h2>
    <p>Enter the file details below to download directly to the VPS storage.</p>
    
    {message}

    <form method="POST" action="/">
        <div class="form-group">
            <label for="url">File URL:</label>
            <input type="text" id="url" name="url" placeholder="https://example.com/file.zip" required>
        </div>
        <div class="form-group">
            <label for="name">Save Name (with extension):</label>
            <input type="text" id="name" name="name" placeholder="file.zip" required>
        </div>
        <div class="form-group">
            <label for="dir">Save Directory (Absolute or Relative):</label>
            <input type="text" id="dir" name="dir" placeholder="./downloads" required>
        </div>
        <div class="actions">
            <button type="submit" class="btn btn-primary">Start Download</button>
            <a href="/shutdown" class="btn btn-danger" onclick="return confirm('Are you sure you want to stop the server? This will unblock your CI/CD pipeline.');">Stop Server & Exit</a>
        </div>
    </form>
</body>
</html>
"""

class DownloadHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Serves the initial HTML form or handles shutdown."""
        if self.path == '/shutdown':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            shutdown_html = """
            <html><body>
            <h2>Server Stopping...</h2>
            <p>The Python server process has been terminated. Your workflow should now continue.</p>
            </body></html>
            """
            self.wfile.write(shutdown_html.encode('utf-8'))
            
            print("\nShutdown request received. Stopping server...")
            # We must run shutdown in a separate thread because it blocks until the request finishes
            threading.Thread(target=self.server.shutdown).start()
            return

        # Normal page load
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_FORM.format(message="").encode('utf-8'))

    def do_POST(self):
        """Handles the form submission and downloads the file."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        fields = urllib.parse.parse_qs(post_data)
        
        url = fields.get('url', [''])[0].strip()
        name = fields.get('name', [''])[0].strip()
        save_dir = fields.get('dir', [''])[0].strip()
        
        message_html = ""
        
        if url and name and save_dir:
            try:
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                
                full_path = os.path.join(save_dir, name)
                
                req = urllib.request.Request(
                    url, 
                    headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
                )
                
                with urllib.request.urlopen(req) as response, open(full_path, 'wb') as out_file:
                    out_file.write(response.read())
                
                message_html = f'<div class="message success">Successfully downloaded to: <code>{full_path}</code></div>'
            except Exception as e:
                message_html = f'<div class="message error">Error: {str(e)}</div>'
        else:
            message_html = '<div class="message error">All fields are required.</div>'

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_FORM.format(message=message_html).encode('utf-8'))

if __name__ == "__main__":
    # Allow address reuse so running the pipeline repeatedly doesn't error out on "Port already in use"
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), DownloadHandler) as httpd:
        print(f"Server running on port {PORT}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
        print("Server successfully stopped. Exiting script.")