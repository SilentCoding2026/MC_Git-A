import http.server
import socketserver
import urllib.parse
import urllib.request
import os
import threading
import json

PORT = 8082

HTML_FORM = """<!DOCTYPE html>
<html>
<head>
    <title>VPS Remote Downloader</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; line-height: 1.6; background-color: #f9f9f9; color: #333; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 25px; }}
        .form-group {{ margin-bottom: 15px; }}
        label {{ display: block; font-weight: bold; margin-bottom: 5px; }}
        input[type="text"], textarea {{ width: 100%; padding: 10px; box-sizing: border-box; border: 1px solid #ccc; border-radius: 4px; font-family: inherit; }}
        textarea {{ resize: vertical; }}
        .btn {{ color: white; padding: 10px 20px; border: none; cursor: pointer; font-size: 16px; text-decoration: none; display: inline-block; border-radius: 4px; font-weight: bold; }}
        .btn-primary {{ background-color: #007BFF; }}
        .btn-primary:hover {{ background-color: #0056b3; }}
        .btn-success {{ background-color: #28a745; }}
        .btn-success:hover {{ background-color: #218838; }}
        .btn-danger {{ background-color: #DC3545; }}
        .btn-danger:hover {{ background-color: #bd2130; }}
        .message {{ padding: 15px; margin-bottom: 20px; border-radius: 4px; white-space: pre-line; font-family: monospace; }}
        .success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
        .error {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
        .actions {{ margin-top: 20px; display: flex; gap: 10px; justify-content: space-between; }}
        .flex-group {{ display: flex; gap: 10px; }}
        hr {{ border: 0; height: 1px; background: #eee; margin: 25px 0; }}
    </style>
</head>
<body>
    <h2>VPS Remote Downloader</h2>
    <p>Fetch files directly to your VPS environment seamlessly.</p>
    
    {message}

    <div class="card">
        <h3>Single File Download</h3>
        <form method="POST" action="/single">
            <div class="form-group">
                <label for="url">File URL:</label>
                <input type="text" id="url" name="url" placeholder="https://example.com/file.zip">
            </div>
            <div class="form-group">
                <label for="name">Save Name (with extension):</label>
                <input type="text" id="name" name="name" placeholder="file.zip">
            </div>
            <div class="form-group">
                <label for="dir">Save Directory:</label>
                <input type="text" id="dir" name="dir" placeholder="./downloads">
            </div>
            <button type="submit" class="btn btn-primary">Start Download</button>
        </form>
    </div>

    <div class="card">
        <h3>Batch JSON Download</h3>
        <form method="POST" action="/batch">
            <div class="form-group">
                <label for="json_data">Paste JSON Array:</label>
                <textarea id="json_data" name="json_data" rows="8" placeholder='[\n  {{\n    "url": "https://example.com/file1.zip",\n    "name": "file1.zip",\n    "save_dir": "./downloads"\n  }}\n]'></textarea>
            </div>
            <button type="submit" class="btn btn-success">Download All Files</button>
        </form>
    </div>

    <div class="actions">
        <span></span> <a href="/shutdown" class="btn btn-danger" onclick="return confirm('Are you sure you want to stop the server? This will unblock your workflow pipeline.');">Stop Server & Exit</a>
    </div>
</body>
</html>
"""

def download_file(url, name, save_dir):
    """Helper to process individual file downloads."""
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    full_path = os.path.join(save_dir, name)
    req = urllib.request.Request(
        url, 
        headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    )
    with urllib.request.urlopen(req) as response, open(full_path, 'wb') as out_file:
        out_file.write(response.read())
    return full_path

class DownloadHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/shutdown':
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            shutdown_html = "<html><body><h2>Server Stopping...</h2><p>Process terminated. CI/CD workflow unblocked.</p></body></html>"
            self.wfile.write(shutdown_html.encode('utf-8'))
            print("\nShutdown request received. Stopping server...")
            threading.Thread(target=self.server.shutdown).start()
            return

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_FORM.format(message="").encode('utf-8'))

    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        fields = urllib.parse.parse_qs(post_data)
        
        message_html = ""
        
        # Route 1: Single File download handling
        if self.path == '/single':
            url = fields.get('url', [''])[0].strip()
            name = fields.get('name', [''])[0].strip()
            save_dir = fields.get('dir', [''])[0].strip()
            
            if url and name and save_dir:
                try:
                    path = download_file(url, name, save_dir)
                    message_html = f'<div class="message success">Successfully downloaded:\n{path}</div>'
                except Exception as e:
                    message_html = f'<div class="message error">Error downloading file:\n{str(e)}</div>'
            else:
                message_html = '<div class="message error">All single fields are required.</div>'
                
        # Route 2: Batch JSON handling
        elif self.path == '/batch':
            json_str = fields.get('json_data', [''])[0].strip()
            if json_str:
                try:
                    tasks = json.loads(json_str)
                    if not isinstance(tasks, list):
                        raise ValueError("JSON input must be a root list/array containing file items.")
                    
                    results = []
                    success_count = 0
                    
                    for i, item in enumerate(tasks):
                        b_url = item.get('url', '').strip()
                        b_name = item.get('name', '').strip()
                        b_dir = item.get('save_dir', '').strip()
                        
                        if b_url and b_name and b_dir:
                            try:
                                path = download_file(b_url, b_name, b_dir)
                                results.append(f"[{i+1}/{len(tasks)}] SUCCESS: {b_name} -> {path}")
                                success_count += 1
                            except Exception as item_err:
                                results.append(f"[{i+1}/{len(tasks)}] FAILED: {b_name} | Error: {str(item_err)}")
                        else:
                            results.append(f"[{i+1}/{len(tasks)}] FAILED: Missing required keys (url, name, or save_dir)")
                    
                    summary_log = "\n".join(results)
                    status_class = "success" if success_count == len(tasks) else "error"
                    message_html = f'<div class="message {status_class}">Batch Completed ({success_count}/{len(tasks)} items downloaded):\n\n{summary_log}</div>'
                    
                except json.JSONDecodeError as je:
                    message_html = f'<div class="message error">Invalid JSON formatting syntax:\n{str(je)}</div>'
                except Exception as e:
                    message_html = f'<div class="message error">Batch processing failed:\n{str(e)}</div>'
            else:
                message_html = '<div class="message error">Please provide JSON configuration details.</div>'

        # Render original UI with status report block
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_FORM.format(message=message_html).encode('utf-8'))

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), DownloadHandler) as httpd:
        print(f"Server up and running on port {PORT}...")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass