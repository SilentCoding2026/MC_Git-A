import http.server
import socketserver
import urllib.parse
import urllib.request
import os
import cgi

PORT = 8082

HTML_FORM = """<!DOCTYPE html>
<html>
<head>
    <title>VPS Remote Downloader</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; line-height: 1.6; }
        .form-group { margin-bottom: 15px; }
        label { display: block; font-weight: bold; margin-bottom: 5px; }
        input[type="text"] { width: 100%; padding: 8px; box-sizing: border-box; }
        button { background-color: #007BFF; color: white; padding: 10px 15px; border: none; cursor: pointer; font-size: 16px; }
        button:hover { background-color: #0056b3; }
        .message { padding: 10px; margin-top: 20px; border-radius: 4px; }
        .success { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
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
        <button type="submit">Start Download</button>
    </form>
</body>
</html>
"""

class DownloadHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """Serves the initial HTML form."""
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        # Render form without any status message
        self.wfile.write(HTML_FORM.format(message="").encode('utf-8'))

    def do_POST(self):
        """Handles the form submission and downloads the file."""
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length).decode('utf-8')
        fields = urllib.parse.parse_qs(post_data)
        
        # Extract fields securely
        url = fields.get('url', [''])[0].strip()
        name = fields.get('name', [''])[0].strip()
        save_dir = fields.get('dir', [''])[0].strip()
        
        message_html = ""
        
        if url and name and save_dir:
            try:
                # Create directory if it doesn't exist
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                
                full_path = os.path.join(save_dir, name)
                
                # Download the file directly via VPS internet connection
                # Using a User-Agent to prevent basic bot blocks from some websites
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

        # Send response back to user
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(HTML_FORM.format(message=message_html).encode('utf-8'))

if __name__ == "__main__":
    # Binding to 0.0.0.0 allows external access to the VPS ip
    with socketserver.TCPServer(("0.0.0.0", PORT), DownloadHandler) as httpd:
        print(f"Server running on port {PORT}...")
        print(f"Access it via http://YOUR_VPS_IP:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")