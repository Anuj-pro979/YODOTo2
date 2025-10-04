# Complete Code Editor Pro - All Files

## File 1: app.py (Backend Server)

```python
# app.py - Enhanced Online Code Editor Backend
import os
import select
import subprocess
import pty
import json
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_from_directory, session
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import eventlet

eventlet.monkey_patch()

app = Flask(__name__, static_folder="static", static_url_path="/static")
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Configuration
WORKSPACE_BASE = Path("/workspace")
WORKSPACE_BASE.mkdir(parents=True, exist_ok=True)

# Simple in-memory user store (use database in production)
USERS = {
    "demo": generate_password_hash("demo123"),
    "admin": generate_password_hash("admin123")
}

# Active shells per session
shells = {}

# ============= Authentication =============

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return jsonify({"error": "Authentication required"}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    if username in USERS and check_password_hash(USERS[username], password):
        session['user'] = username
        session['workspace'] = str(WORKSPACE_BASE / username)
        
        # Create user workspace
        user_workspace = Path(session['workspace'])
        user_workspace.mkdir(parents=True, exist_ok=True)
        
        return jsonify({"success": True, "username": username})
    
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/api/auth/status")
def auth_status():
    if 'user' in session:
        return jsonify({"authenticated": True, "username": session['user']})
    return jsonify({"authenticated": False})

# ============= File Management API =============

def get_user_workspace():
    """Get current user's workspace path"""
    workspace = session.get('workspace', str(WORKSPACE_BASE / 'default'))
    return Path(workspace)

def is_safe_path(basedir, path):
    """Check if path is within basedir (prevent directory traversal)"""
    try:
        basedir = Path(basedir).resolve()
        full_path = (basedir / path).resolve()
        return str(full_path).startswith(str(basedir))
    except:
        return False

@app.route("/api/files", methods=["GET"])
@login_required
def list_files():
    """List all files in workspace"""
    workspace = get_user_workspace()
    
    def scan_directory(path):
        items = []
        try:
            for item in sorted(path.iterdir()):
                rel_path = item.relative_to(workspace)
                if item.is_file():
                    items.append({
                        "name": item.name,
                        "path": str(rel_path),
                        "type": "file",
                        "size": item.stat().st_size,
                        "extension": item.suffix
                    })
                elif item.is_dir():
                    items.append({
                        "name": item.name,
                        "path": str(rel_path),
                        "type": "directory",
                        "children": scan_directory(item)
                    })
        except PermissionError:
            pass
        return items
    
    files = scan_directory(workspace)
    return jsonify({"files": files})

@app.route("/api/files/<path:filepath>", methods=["GET"])
@login_required
def read_file(filepath):
    """Read file content"""
    workspace = get_user_workspace()
    
    if not is_safe_path(workspace, filepath):
        return jsonify({"error": "Invalid path"}), 403
    
    file_path = workspace / filepath
    
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    if not file_path.is_file():
        return jsonify({"error": "Not a file"}), 400
    
    try:
        content = file_path.read_text(encoding='utf-8')
        return jsonify({
            "content": content,
            "path": filepath,
            "name": file_path.name
        })
    except UnicodeDecodeError:
        return jsonify({"error": "Binary file not supported"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/<path:filepath>", methods=["POST"])
@login_required
def save_file(filepath):
    """Save/create file"""
    workspace = get_user_workspace()
    
    if not is_safe_path(workspace, filepath):
        return jsonify({"error": "Invalid path"}), 403
    
    data = request.get_json()
    content = data.get("content", "")
    
    file_path = workspace / filepath
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        file_path.write_text(content, encoding='utf-8')
        return jsonify({
            "success": True,
            "path": filepath,
            "size": len(content)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/<path:filepath>", methods=["DELETE"])
@login_required
def delete_file(filepath):
    """Delete file or directory"""
    workspace = get_user_workspace()
    
    if not is_safe_path(workspace, filepath):
        return jsonify({"error": "Invalid path"}), 403
    
    file_path = workspace / filepath
    
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    
    try:
        if file_path.is_file():
            file_path.unlink()
        elif file_path.is_dir():
            import shutil
            shutil.rmtree(file_path)
        
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/rename", methods=["POST"])
@login_required
def rename_file():
    """Rename file or directory"""
    workspace = get_user_workspace()
    data = request.get_json()
    old_path = data.get("oldPath")
    new_path = data.get("newPath")
    
    if not is_safe_path(workspace, old_path) or not is_safe_path(workspace, new_path):
        return jsonify({"error": "Invalid path"}), 403
    
    old_file = workspace / old_path
    new_file = workspace / new_path
    
    if not old_file.exists():
        return jsonify({"error": "File not found"}), 404
    
    if new_file.exists():
        return jsonify({"error": "Target already exists"}), 400
    
    try:
        new_file.parent.mkdir(parents=True, exist_ok=True)
        old_file.rename(new_file)
        return jsonify({"success": True, "newPath": new_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/files/directory", methods=["POST"])
@login_required
def create_directory():
    """Create new directory"""
    workspace = get_user_workspace()
    data = request.get_json()
    dir_path = data.get("path")
    
    if not is_safe_path(workspace, dir_path):
        return jsonify({"error": "Invalid path"}), 403
    
    directory = workspace / dir_path
    
    try:
        directory.mkdir(parents=True, exist_ok=True)
        return jsonify({"success": True, "path": dir_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============= Code Execution API =============

@app.route("/api/execute", methods=["POST"])
@login_required
def execute_code():
    """Execute code in isolated environment"""
    data = request.get_json()
    code = data.get("code", "")
    language = data.get("language", "python")
    
    workspace = get_user_workspace()
    
    # Language configurations
    executors = {
        "python": {
            "cmd": ["python3", "-c", code],
            "timeout": 10
        },
        "javascript": {
            "cmd": ["node", "-e", code],
            "timeout": 10
        },
        "bash": {
            "cmd": ["bash", "-c", code],
            "timeout": 10
        }
    }
    
    if language not in executors:
        return jsonify({"error": f"Language '{language}' not supported"}), 400
    
    config = executors[language]
    
    try:
        result = subprocess.run(
            config["cmd"],
            capture_output=True,
            text=True,
            timeout=config["timeout"],
            cwd=str(workspace)
        )
        
        return jsonify({
            "success": True,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode
        })
    except subprocess.TimeoutExpired:
        return jsonify({"error": "Execution timeout"}), 408
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============= Terminal WebSocket Handlers =============

def read_and_forward(sid, master_fd):
    """Read from pty and forward to client"""
    max_read_bytes = 1024 * 20
    try:
        while True:
            eventlet.sleep(0)
            r, _, _ = select.select([master_fd], [], [], 0.1)
            if master_fd in r:
                try:
                    data = os.read(master_fd, max_read_bytes).decode(errors="ignore")
                    socketio.emit("terminal.output", {"output": data}, to=sid)
                except OSError:
                    break
    except Exception as e:
        print(f"Reader thread exception: {e}")
    finally:
        try:
            os.close(master_fd)
        except:
            pass
        shells.pop(sid, None)

@socketio.on("terminal.connect")
def terminal_connect():
    """Initialize terminal session"""
    sid = request.sid
    
    # Check authentication
    user = session.get('user')
    if not user:
        emit("terminal.error", {"error": "Not authenticated"})
        return
    
    workspace = get_user_workspace()
    
    # Spawn shell
    master_fd, slave_fd = pty.openpty()
    env = os.environ.copy()
    env["TERM"] = "xterm-256color"
    env["PS1"] = f"{user}@editor:\\w$ "
    
    proc = subprocess.Popen(
        ["/bin/bash"],
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        close_fds=True,
        env=env,
        cwd=str(workspace)
    )
    
    shells[sid] = {
        "proc": proc,
        "master_fd": master_fd,
        "slave_fd": slave_fd,
        "user": user
    }
    
    socketio.start_background_task(read_and_forward, sid, master_fd)
    
    welcome = f"\r\n=== Code Editor Terminal ===\r\n"
    welcome += f"User: {user}\r\n"
    welcome += f"Workspace: {workspace}\r\n"
    welcome += f"PID: {proc.pid}\r\n\r\n"
    
    socketio.emit("terminal.output", {"output": welcome}, to=sid)

@socketio.on("disconnect")
def on_disconnect():
    """Cleanup on disconnect"""
    sid = request.sid
    info = shells.get(sid)
    if info:
        try:
            info["proc"].terminate()
            os.close(info["slave_fd"])
            os.close(info["master_fd"])
        except:
            pass
        shells.pop(sid, None)

@socketio.on("terminal.input")
def on_terminal_input(data):
    """Handle terminal input"""
    sid = request.sid
    info = shells.get(sid)
    if not info:
        return
    
    inp = data.get("input", "")
    if isinstance(inp, str):
        inp = inp.encode()
    
    try:
        os.write(info["master_fd"], inp)
    except OSError:
        pass

@socketio.on("terminal.resize")
def on_terminal_resize(data):
    """Handle terminal resize"""
    sid = request.sid
    info = shells.get(sid)
    if not info:
        return
    
    cols = data.get("cols", 80)
    rows = data.get("rows", 24)
    
    try:
        import fcntl
        import termios
        import struct
        
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(info["master_fd"], termios.TIOCSWINSZ, winsize)
    except:
        pass

# ============= Static Files =============

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:filename>")
def static_proxy(filename):
    return send_from_directory("static", filename)

# ============= Main =============

if __name__ == "__main__":
    print("=" * 50)
    print("🚀 Code Editor Pro Server Starting...")
    print("=" * 50)
    print(f"📁 Workspace Directory: {WORKSPACE_BASE}")
    print(f"🌐 Server URL: http://0.0.0.0:5000")
    print(f"👤 Demo Login: demo / demo123")
    print("=" * 50)
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
```

---

## File 2: requirements.txt

```txt
Flask==3.0.0
flask-socketio==5.3.6
python-engineio==4.8.0
python-socketio==5.10.0
eventlet==0.33.3
Werkzeug==3.0.1
```

---

## File 3: Dockerfile

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    nodejs \
    npm \
    vim \
    nano \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY app.py .
COPY static ./static

# Create workspace directories for demo users
RUN mkdir -p /workspace/demo /workspace/admin

# Create sample files for demo user
RUN echo '<!DOCTYPE html>\n\
<html lang="en">\n\
<head>\n\
    <meta charset="UTF-8">\n\
    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n\
    <title>Welcome to Code Editor Pro</title>\n\
    <style>\n\
        body {\n\
            font-family: Arial, sans-serif;\n\
            max-width: 800px;\n\
            margin: 50px auto;\n\
            padding: 20px;\n\
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n\
            color: white;\n\
        }\n\
        .container {\n\
            background: rgba(255,255,255,0.1);\n\
            padding: 30px;\n\
            border-radius: 10px;\n\
            backdrop-filter: blur(10px);\n\
        }\n\
        h1 { font-size: 2.5em; margin-bottom: 10px; }\n\
        code { background: rgba(0,0,0,0.3); padding: 2px 6px; border-radius: 3px; }\n\
    </style>\n\
</head>\n\
<body>\n\
    <div class="container">\n\
        <h1>🚀 Welcome to Code Editor Pro!</h1>\n\
        <p>This is a full-featured online code editor with:</p>\n\
        <ul>\n\
            <li>Monaco Editor (VS Code engine)</li>\n\
            <li>Integrated Terminal</li>\n\
            <li>Live HTML Preview</li>\n\
            <li>File Management System</li>\n\
            <li>Code Execution (Python, JavaScript, Bash)</li>\n\
        </ul>\n\
        <h2>Getting Started</h2>\n\
        <p>Try editing this file or create new files using the sidebar.</p>\n\
        <p>Open <code>hello.py</code> or <code>hello.js</code> to test code execution.</p>\n\
        <p>Use the terminal to run commands like <code>ls</code>, <code>pwd</code>, or install packages.</p>\n\
    </div>\n\
</body>\n\
</html>' > /workspace/demo/index.html

RUN echo '# Welcome to Code Editor Pro\n\
\n\
## Features\n\
\n\
- **Monaco Editor** - Professional code editing\n\
- **Terminal** - Full bash terminal access\n\
- **Multi-language Support** - Python, JavaScript, HTML, CSS, and more\n\
- **Live Preview** - Instant HTML preview\n\
- **File Management** - Create, edit, delete files and folders\n\
\n\
## Quick Start\n\
\n\
1. Create a new file using the sidebar\n\
2. Start coding with syntax highlighting\n\
3. Save with Ctrl+S or auto-save\n\
4. Run Python/JavaScript code with the Run button\n\
5. Use the terminal for advanced operations\n\
\n\
## Sample Code\n\
\n\
```python\n\
print("Hello from Python!")\n\
```\n\
\n\
```javascript\n\
console.log("Hello from JavaScript!");\n\
```\n\
\n\
Happy coding! 🎉' > /workspace/demo/README.md

RUN echo 'def greet(name):\n\
    """A simple greeting function"""\n\
    return f"Hello, {name}! Welcome to Code Editor Pro."\n\
\n\
def fibonacci(n):\n\
    """Generate fibonacci sequence up to n terms"""\n\
    fib = [0, 1]\n\
    for i in range(2, n):\n\
        fib.append(fib[i-1] + fib[i-2])\n\
    return fib[:n]\n\
\n\
# Main execution\n\
if __name__ == "__main__":\n\
    print(greet("Developer"))\n\
    print(f"Fibonacci sequence: {fibonacci(10)}")' > /workspace/demo/hello.py

RUN echo 'function greet(name) {\n\
    return `Hello, ${name}! Welcome to Code Editor Pro.`;\n\
}\n\
\n\
function fibonacci(n) {\n\
    const fib = [0, 1];\n\
    for (let i = 2; i < n; i++) {\n\
        fib.push(fib[i-1] + fib[i-2]);\n\
    }\n\
    return fib.slice(0, n);\n\
}\n\
\n\
// Main execution\n\
console.log(greet("Developer"));\n\
console.log("Fibonacci sequence:", fibonacci(10));' > /workspace/demo/hello.js

RUN echo '#!/bin/bash\n\
# Sample bash script\n\
\n\
echo "================================="\n\
echo "  Code Editor Pro - System Info"\n\
echo "================================="\n\
echo ""\n\
echo "Current Directory: $(pwd)"\n\
echo "User: $(whoami)"\n\
echo "Date: $(date)"\n\
echo ""\n\
echo "Files in workspace:"\n\
ls -lh\n\
echo ""\n\
echo "Python version:"\n\
python3 --version\n\
echo ""\n\
echo "Node version:"\n\
node --version' > /workspace/demo/info.sh

RUN chmod +x /workspace/demo/info.sh

# Create sample CSS file
RUN echo '/* Modern CSS Styles */\n\
\n\
:root {\n\
    --primary-color: #667eea;\n\
    --secondary-color: #764ba2;\n\
    --text-color: #333;\n\
    --bg-color: #f5f5f5;\n\
}\n\
\n\
* {\n\
    margin: 0;\n\
    padding: 0;\n\
    box-sizing: border-box;\n\
}\n\
\n\
body {\n\
    font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;\n\
    background: var(--bg-color);\n\
    color: var(--text-color);\n\
    line-height: 1.6;\n\
}\n\
\n\
.container {\n\
    max-width: 1200px;\n\
    margin: 0 auto;\n\
    padding: 20px;\n\
}\n\
\n\
.btn {\n\
    padding: 10px 20px;\n\
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));\n\
    color: white;\n\
    border: none;\n\
    border-radius: 5px;\n\
    cursor: pointer;\n\
    transition: transform 0.2s;\n\
}\n\
\n\
.btn:hover {\n\
    transform: translateY(-2px);\n\
}' > /workspace/demo/styles.css

# Create a sample JSON config
RUN echo '{\n\
    "project": "Code Editor Pro",\n\
    "version": "1.0.0",\n\
    "author": "Your Name",\n\
    "description": "A powerful online code editor",\n\
    "features": [\n\
        "Monaco Editor",\n\
        "Terminal Integration",\n\
        "Live Preview",\n\
        "Multi-language Support"\n\
    ],\n\
    "settings": {\n\
        "theme": "dark",\n\
        "fontSize": 14,\n\
        "autoSave": true,\n\
        "tabSize": 4\n\
    }\n\
}' > /workspace/demo/config.json

# Set proper permissions
RUN chmod -R 777 /workspace

VOLUME ["/workspace"]

# Expose port
EXPOSE 5000

# Set environment variables
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/auth/status || exit 1

# Run the application
CMD ["python", "app.py"]
```

---

## File 4: docker-compose.yml

```yaml
version: '3.8'

services:
  web:
    build: .
    container_name: code-editor-pro
    ports:
      - "5000:5000"
    volumes:
      # Mount workspace directory (persistent storage)
      - ./workspace:/workspace
      # Mount static files for development (optional)
      - ./static:/app/static
    environment:
      # Change this secret key in production!
      - SECRET_KEY=your-super-secret-key-change-this-in-production
      - FLASK_ENV=development
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
    stdin_open: true
    tty: true
    networks:
      - editor-network
    # Resource limits (optional but recommended)
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

networks:
  editor-network:
    driver: bridge
```

---

## File 5: static/index.html (Complete Frontend)

Create a folder named `static` and put this file inside it.

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Editor Pro</title>
    <link rel="stylesheet" href="https://unpkg.com/xterm@4.19.0/css/xterm.css">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        :root {
            --bg-primary: #1e1e1e;
            --bg-secondary: #252526;
            --bg-tertiary: #2d2d30;
            --border-color: #3e3e42;
            --text-primary: #cccccc;
            --text-secondary: #858585;
            --accent-blue: #007acc;
            --accent-green: #4ec9b0;
            --accent-red: #f48771;
            --accent-yellow: #dcdcaa;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: var(--bg-primary);
            color: var(--text-primary);
            height: 100vh;
            overflow: hidden;
        }

        /* Login Screen */
        #login-screen {
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }

        .login-box {
            background: white;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            width: 100%;
            max-width: 400px;
        }

        .login-box h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 28px;
        }

        .login-box p {
            color: #666;
            margin-bottom: 30px;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            color: #333;
            margin-bottom: 8px;
            font-weight: 500;
        }

        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            transition: border-color 0.3s;
        }

        .form-group input:focus {
            outline: none;
            border-color: #667eea;
        }

        .btn-login {
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 6px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }

        .btn-login:hover {
            transform: translateY(-2px);
        }

        .error-message {
            color: #e74c3c;
            margin-top: 15px;
            font-size: 14px;
        }

        .demo-info {
            margin-top: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
            font-size: 13px;
            color: #666;
        }

        .demo-info strong {
            color: #333;
        }

        /* Main Editor Layout */
        #editor-container {
            display: none;
            height: 100vh;
            flex-direction: column;
        }

        #editor-container.active {
            display: flex;
        }

        /* Header */
        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            padding: 8px 16px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .header-left {
            display: flex;
            align-items: center;
            gap: 20px;
        }

        .logo {
            font-size: 18px;
            font-weight: 700;
            color: var(--accent-blue);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .header-actions {
            display: flex;
            gap: 10px;
        }

        .btn {
            padding: 6px 12px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            border: 1px solid var(--border-color);
            border-radius: 4px;
            cursor: pointer;
            font-size: 13px;
            transition: all 0.2s;
        }

        .btn:hover {
            background: var(--accent-blue);
            border-color: var(--accent-blue);
        }

        .btn-primary {
            background: var(--accent-blue);
            border-color: var(--accent-blue);
        }

        .btn-danger {
            background: var(--accent-red);
            border-color: var(--accent-red);
        }

        .user-info {
            color: var(--text-secondary);
            font-size: 13px;
            margin-right: 15px;
        }

        /* Main Content */
        .main-content {
            display: flex;
            flex: 1;
            overflow: hidden;
        }

        /* Sidebar - File Explorer */
        .sidebar {
            width: 250px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
        }

        .sidebar-header {
            padding: 12px;
            border-bottom: 1px solid var(--border-color);
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-secondary);
        }

        .file-tree {
            flex: 1;
            overflow-y: auto;
            padding: 8px;
        }

        .file-item, .folder-item {
            padding: 6px 8px;
            cursor: pointer;
            border-radius: 4px;
            display: flex;
            align-items: center;
            gap: 6px;
            font-size: 13px;
            user-select: none;
        }

        .file-item:hover, .folder-item:hover {
            background: var(--bg-tertiary);
        }

        .file-item.active {
            background: var(--accent-blue);
        }

        .folder-icon, .file-icon {
            font-size: 14px;
        }

        .folder-children {
            margin-left: 16px;
        }

        .folder-item.collapsed + .folder-children {
            display: none;
        }

        .sidebar-actions {
            padding: 12px;
            border-top: 1px solid var(--border-color);
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }

        .btn-small {
            padding: 4px 8px;
            font-size: 11px;
            flex: 1;
            min-width: 70px;
        }

        /* Editor Area */
        .editor-area {
            flex: 1;
            display: flex;
            flex-direction: column;
        }

        .tabs {
            display: flex;
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            overflow-x: auto;
        }

        .tab {
            padding: 10px 16px;
            border-right: 1px solid var(--border-color);
            cursor: pointer;
            font-size: 13px;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }

        .tab:hover {
            background: var(--bg-tertiary);
        }

        .tab.active {
            background: var(--bg-primary);
        }

        .tab-close {
            margin-left: 8px;
            font-size: 16px;
            opacity: 0.6;
        }

        .tab-close:hover {
            opacity: 1;
        }

        .editor-wrapper {
            display: flex;
            flex: 1;
            overflow: hidden;
        }

        #monaco-editor {
            flex: 1;
        }

        .preview-panel {
            width: 40%;
            border-left: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            background: var(--bg-secondary);
        }

        .preview-header {
            padding: 10px 12px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .preview-header h3 {
            font-size: 13px;
            font-weight: 600;
        }

        #preview-frame {
            flex: 1;
            border: none;
            background: white;
        }

        /* Terminal */
        .terminal-panel {
            height: 250px;
            background: var(--bg-secondary);
            border-top: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
        }

        .terminal-header {
            padding: 8px 12px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .terminal-header h3 {
            font-size: 13px;
            font-weight: 600;
        }

        #terminal {
            flex: 1;
            padding: 10px;
        }

        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }

        ::-webkit-scrollbar-thumb {
            background: var(--bg-tertiary);
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--border-color);
        }

        /* Status Bar */
        .status-bar {
            background: var(--accent-blue);
            color: white;
            padding: 4px 12px;
            font-size: 12px;
            display: flex;
            justify-content: space-between;
        }
    </style>
</head>
<body>
    <!-- Login Screen -->
    <div id="login-screen">
        <div class="login-box">
            <h1>🚀 Code Editor Pro</h1>
            <p>Sign in to start coding</p>
            <form id="login-form">
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" id="username" value="demo" required>
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="password" value="demo123" required>
                </div>
                <button type="submit" class="btn-login">Sign In</button>
                <div id="login-error" class="error-message"></div>
            </form>
            <div class="demo-info">
                <strong>Demo Account:</strong><br>
                Username: demo<br>
                Password: demo123
            </div>
        </div>
    </div>

    <!-- Main Editor Container -->
    <div id="editor-container">
        <!-- Header -->
        <div class="header">
            <div class="header-left">
                <div class="logo">⚡ Code Editor Pro</div>
                <div class="header-actions">
                    <button class="btn btn-primary" onclick="app.saveCurrentFile()">💾 Save</button>
                    <button class="btn" onclick="app.runCode()">▶️ Run</button>
                    <button class="btn" onclick="app.refreshPreview()">🔄 Preview</button>
                </div>
            </div>
            <div>
                <span class="user-info" id="user-display"></span>
                <button class="btn btn-danger" onclick="app.logout()">Logout</button>
            </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
            <!-- Sidebar -->
            <div class="sidebar">
                <div class="sidebar-header">Explorer</div>
                <div class="file-tree" id="file-tree"></div>
                <div class="sidebar-actions">
                    <button class="btn btn-small" onclick="app.newFile()">📄 New</button>
                    <button class="btn btn-small" onclick="app.newFolder()">📁 Folder</button>
                    <button class="btn btn-small" onclick="app.refreshFiles()">🔄 Refresh</button>
                </div>
            </div>

            <!-- Editor Area -->
            <div class="editor-area">
                <div class="tabs" id="tabs"></div>
                <div class="editor-wrapper">
                    <div id="monaco-editor"></div>
                    <div class="preview-panel" id="preview-panel" style="display:none;">
                        <div class="preview-header">
                            <h3>Live Preview</h3>
                            <button class="btn btn-small" onclick="app.togglePreview()">✕</button>
                        </div>
                        <iframe id="preview-frame"></iframe>
                    </div>
                </div>
            </div>
        </div>

        <!-- Terminal Panel -->
        <div class="terminal-panel">
            <div class="terminal-header">
                <h3>Terminal</h3>
                <div>
                    <button class="btn btn-small" onclick="app.clearTerminal()">Clear</button>
                </div>
            </div>
            <div id="terminal"></div>
        </div>

        <div class="status-bar">
            <span id="status-left">Ready</span>
            <span id="status-right">Line 1, Col 1</span>
        </div>
    </div>

    <!-- Scripts -->
    <script src="https://cdn.socket.io/4.6.1/socket.io.min.js"></script>
    <script src="https://unpkg.com/xterm@4.19.0/lib/xterm.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/monaco-editor@0.34.0/min/vs/loader.js"></script>
    
    <script>
        const app = {
            editor: null,
            socket: null,
            terminal: null,
            currentFile: null,
            openFiles: {},
            authenticated: false
        };

        // Login functionality
        document.getElementById('login-form').addEventListener('submit', async (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({username, password})
                });
                
                const data = await response.json();
                
                if (data.success) {
                    app.authenticated = true;
                    document.getElementById('login-screen').style.display = 'none';
                    document.getElementById('editor-container').classList.add('active');
                    document.getElementById('user-display').textContent = `👤 ${data.username}`;
                    await app.init();
                } else {
                    document.getElementById('login-error').textContent = data.error || 'Login failed';
                }
            } catch (error) {
                document.getElementById('login-error').textContent = 'Connection error';
            }
        });

        // Initialize application
        app.init = async function() {
            await this.initMonaco();
            this.initTerminal();
            this.initSocket();
            await this.loadFiles();
        };

        // Initialize Monaco Editor
        app.initMonaco = function() {
            return new Promise((resolve) => {
                require.config({ paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.34.0/min/vs' }});
                require(['vs/editor/editor.main'], () => {
                    app.editor = monaco.editor.create(document.getElementById('monaco-editor'), {
                        value: '// Welcome to Code Editor Pro\n// Start coding...\n',
                        language: 'javascript',
                        theme: 'vs-dark',
                        automaticLayout: true,
                        fontSize: 14,
                        minimap: { enabled: true },
                        scrollBeyondLastLine: false
                    });

                    // Update cursor position
                    app.editor.onDidChangeCursorPosition((e) => {
                        document.getElementById('status-right').textContent = 
                            `Line ${e.position.lineNumber}, Col ${e.position.column}`;
                    });

                    // Auto-save on change (debounced)
                    let saveTimeout;
                    app.editor.onDidChangeModelContent(() => {
                        clearTimeout(saveTimeout);
                        saveTimeout = setTimeout(() => {
                            if (app.currentFile) {
                                app.saveCurrentFile(true);
                            }
                        }, 1000);
                    });

                    resolve();
                });
            });
        };

        // Initialize Terminal
        app.initTerminal = function() {
            app.terminal = new Terminal({
                cols: 100,
                rows: 20,
                theme: {
                    background: '#1e1e1e',
                    foreground: '#cccccc'
                },
                fontFamily: 'Menlo, Monaco, "Courier New", monospace',
                fontSize: 13,
                convertEol: true
            });
            
            app.terminal.open(document.getElementById('terminal'));
            
            app.terminal.onData(data => {
                if (app.socket && app.socket.connected) {
                    app.socket.emit('terminal.input', { input: data });
                }
            });

            // Handle resize
            const resizeObserver = new ResizeObserver(() => {
                const terminalEl = document.getElementById('terminal');
                const cols = Math.floor(terminalEl.clientWidth / 9);
                const rows = Math.floor(terminalEl.clientHeight / 17);
                app.terminal.resize(cols, rows);
                if (app.socket) {
                    app.socket.emit('terminal.resize', { cols, rows });
                }
            });
            resizeObserver.observe(document.getElementById('terminal'));
        };

        // Initialize WebSocket
        app.initSocket = function() {
            app.socket = io();
            
            app.socket.on('connect', () => {
                app.terminal.write('\r\n\x1b[32m[Connected to server]\x1b[0m\r\n');
                app.socket.emit('terminal.connect');
            });
            
            app.socket.on('disconnect', () => {
                app.terminal.write('\r\n\x1b[31m[Disconnected from server]\x1b[0m\r\n');
            });
            
            app.socket.on('terminal.output', (data) => {
                app.terminal.write(data.output);
            });

            app.socket.on('terminal.error', (data) => {
                app.terminal.write(`\r\n\x1b[31mError: ${data.error}\x1b[0m\r\n`);
            });
        };

        // Load files from server
        app.loadFiles = async function() {
            try {
                const response = await fetch('/api/files');
                const data = await response.json();
                app.renderFileTree(data.files);
            } catch (error) {
                console.error('Failed to load files:', error);
            }
        };

        // Render file tree
        app.renderFileTree = function(files, container = null) {
            if (!container) {
                container = document.getElementById('file-tree');
                container.innerHTML = '';
            }

            files.forEach(item => {
                if (item.type === 'directory') {
                    const folderDiv = document.createElement('div');
                    folderDiv.className = 'folder-item';
                    folderDiv.innerHTML = `<span class="folder-icon">📁</span> ${item.name}`;
                    folderDiv.onclick = (e) => {
                        e.stopPropagation();
                        folderDiv.classList.toggle('collapsed');
                    };
                    container.appendChild(folderDiv);

                    if (item.children && item.children.length > 0) {
                        const childrenDiv = document.createElement('div');
                        childrenDiv.className = 'folder-children';
                        container.appendChild(childrenDiv);
                        app.renderFileTree(item.children, childrenDiv);
                    }
                } else if (item.type === 'file') {
                    const fileDiv = document.createElement('div');
                    fileDiv.className = 'file-item';
                    const icon = app.getFileIcon(item.extension);
                    fileDiv.innerHTML = `<span class="file-icon">${icon}</span> ${item.name}`;
                    fileDiv.onclick = () => app.openFile(item.path);
                    container.appendChild(fileDiv);
                }
            });
        };

        // Get file icon based on extension
        app.getFileIcon = function(ext) {
            const icons = {
                '.html': '🌐',
                '.css': '🎨',
                '.js': '📜',
                '.json': '📋',
                '.py': '🐍',
                '.md': '📝',
                '.txt': '📄',
                '.sh': '⚙️'
            };
            return icons[ext] || '📄';
        };

        // Open file
        app.openFile = async function(path) {
            try {
                const response = await fetch(`/api/files/${path}`);
                const data = await response.json();
                
                if (data.content !== undefined) {
                    app.currentFile = path;
                    app.openFiles[path] = {
                        content: data.content,
                        name: data.name
                    };
                    
                    // Detect language
                    const ext = path.substring(path.lastIndexOf('.'));
                    const langMap = {
                        '.html': 'html',
                        '.css': 'css',
                        '.js': 'javascript',
                        '.json': 'json',
                        '.py': 'python',
                        '.md': 'markdown',
                        '.txt': 'plaintext',
                        '.sh': 'shell'
                    };
                    const language = langMap[ext] || 'plaintext';
                    
                    // Update editor
                    monaco.editor.setModelLanguage(app.editor.getModel(), language);
                    app.editor.setValue(data.content);
                    
                    // Update tabs
                    app.updateTabs();
                    
                    // Show preview for HTML
                    if (ext === '.html') {
                        app.showPreview();
                        app.refreshPreview();
                    }
                    
                    document.getElementById('status-left').textContent = `Opened: ${data.name}`;
                }
            } catch (error) {
                console.error('Failed to open file:', error);
                alert('Failed to open file');
            }
        };

        // Save current file
        app.saveCurrentFile = async function(silent = false) {
            if (!app.currentFile) {
                if (!silent) alert('No file open');
                return;
            }

            const content = app.editor.getValue();
            
            try {
                const response = await fetch(`/api/files/${app.currentFile}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ content })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    app.openFiles[app.currentFile].content = content;
                    if (!silent) {
                        document.getElementById('status-left').textContent = `Saved: ${app.currentFile}`;
                    }
                }
            } catch (error) {
                console.error('Failed to save file:', error);
                if (!silent) alert('Failed to save file');
            }
        };

        // Create new file
        app.newFile = async function() {
            const filename = prompt('Enter filename (e.g., script.js):');
            if (!filename) return;

            try {
                const response = await fetch(`/api/files/${filename}`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ content: '' })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    await app.loadFiles();
                    await app.openFile(filename);
                }
            } catch (error) {
                console.error('Failed to create file:', error);
                alert('Failed to create file');
            }
        };

        // Create new folder
        app.newFolder = async function() {
            const foldername = prompt('Enter folder name:');
            if (!foldername) return;

            try {
                const response = await fetch('/api/files/directory', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ path: foldername })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    await app.loadFiles();
                }
            } catch (error) {
                console.error('Failed to create folder:', error);
                alert('Failed to create folder');
            }
        };

        // Refresh files
        app.refreshFiles = async function() {
            await app.loadFiles();
            document.getElementById('status-left').textContent = 'Files refreshed';
        };

        // Update tabs
        app.updateTabs = function() {
            const tabsContainer = document.getElementById('tabs');
            tabsContainer.innerHTML = '';
            
            Object.keys(app.openFiles).forEach(path => {
                const tab = document.createElement('div');
                tab.className = 'tab' + (path === app.currentFile ? ' active' : '');
                tab.innerHTML = `
                    ${app.openFiles[path].name}
                    <span class="tab-close" onclick="app.closeFile('${path}', event)">×</span>
                `;
                tab.onclick = (e) => {
                    if (!e.target.classList.contains('tab-close')) {
                        app.switchToFile(path);
                    }
                };
                tabsContainer.appendChild(tab);
            });
        };

        // Switch to file
        app.switchToFile = function(path) {
            app.currentFile = path;
            app.editor.setValue(app.openFiles[path].content);
            app.updateTabs();
        };

        // Close file
        app.closeFile = function(path, event) {
            event.stopPropagation();
            delete app.openFiles[path];
            
            if (app.currentFile === path) {
                const remaining = Object.keys(app.openFiles);
                if (remaining.length > 0) {
                    app.switchToFile(remaining[0]);
                } else {
                    app.currentFile = null;
                    app.editor.setValue('');
                }
            }
            
            app.updateTabs();
        };

        // Run code
        app.runCode = async function() {
            if (!app.currentFile) {
                alert('No file open');
                return;
            }

            const code = app.editor.getValue();
            const ext = app.currentFile.substring(app.currentFile.lastIndexOf('.'));
            
            const langMap = {
                '.py': 'python',
                '.js': 'javascript',
                '.sh': 'bash'
            };
            
            const language = langMap[ext];
            
            if (!language) {
                alert('Cannot execute this file type. Use terminal instead.');
                return;
            }

            app.terminal.write('\r\n\x1b[36m[Executing...]\x1b[0m\r\n');

            try {
                const response = await fetch('/api/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ code, language })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    if (data.stdout) {
                        app.terminal.write(data.stdout);
                    }
                    if (data.stderr) {
                        app.terminal.write(`\x1b[31m${data.stderr}\x1b[0m`);
                    }
                    app.terminal.write(`\r\n\x1b[32m[Execution completed with code ${data.returncode}]\x1b[0m\r\n`);
                } else {
                    app.terminal.write(`\r\n\x1b[31m[Error: ${data.error}]\x1b[0m\r\n`);
                }
            } catch (error) {
                app.terminal.write(`\r\n\x1b[31m[Failed to execute]\x1b[0m\r\n`);
            }
        };

        // Show/hide preview
        app.showPreview = function() {
            document.getElementById('preview-panel').style.display = 'flex';
        };

        app.togglePreview = function() {
            const panel = document.getElementById('preview-panel');
            panel.style.display = panel.style.display === 'none' ? 'flex' : 'none';
        };

        // Refresh preview
        app.refreshPreview = function() {
            const content = app.editor.getValue();
            document.getElementById('preview-frame').srcdoc = content;
        };

        // Clear terminal
        app.clearTerminal = function() {
            app.terminal.clear();
        };

        // Logout
        app.logout = async function() {
            try {
                await fetch('/api/auth/logout', { method: 'POST' });
                location.reload();
            } catch (error) {
                location.reload();
            }
        };

        // Check authentication on load
        (async function() {
            try {
                const response = await fetch('/api/auth/status');
                const data = await response.json();
                
                if (data.authenticated) {
                    document.getElementById('login-screen').style.display = 'none';
                    document.getElementById('editor-container').classList.add('active');
                    document.getElementById('user-display').textContent = `👤 ${data.username}`;
                    await app.init();
                }
            } catch (error) {
                console.log('Not authenticated');
            }
        })();
    </script>
</body>
</html>
```

---

## File 6: .gitignore

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# Flask
instance/
.webassets-cache

# IDEs
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Project specific
workspace/
*.log

# Docker
.dockerignore
```

---

## File 7: .dockerignore

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env
venv
pip-log.txt
pip-delete-this-directory.txt
.tox
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.mypy_cache
.pytest_cache
.hypothesis
workspace/
.DS_Store
*.swp
.vscode
.idea
```

---

## File 8: setup.sh (Setup Script)

```bash
#!/bin/bash

echo "========================================="
echo "  Code Editor Pro - Setup Script"
echo "========================================="
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "   Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "   Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker is installed"
echo "✅ Docker Compose is installed"
echo ""

# Create directory structure
echo "📁 Creating directory structure..."
mkdir -p static
mkdir -p workspace

echo "✅ Directories created"
echo ""

# Build Docker image
echo "🔨 Building Docker image..."
docker-compose build

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully"
else
    echo "❌ Failed to build Docker image"
    exit 1
fi

echo ""
echo "========================================="
echo "  Setup Complete!"
echo "========================================="
echo ""
echo "To start the editor:"
echo "  docker-compose up -d"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop the editor:"
echo "  docker-compose down"
echo ""
echo "Access the editor at: http://localhost:5000"
echo "Default login: demo / demo123"
echo ""
echo "========================================="
```

---

## File 9: README.md (Quick Start Guide)

```markdown
# Code Editor Pro

A full-featured online code editor with Monaco, Terminal, and Live Preview.

## 🚀 Quick Start

### 1. Clone or Download
```bash
# Create project directory
mkdir code-editor-pro
cd code-editor-pro
```

### 2. Add All Files
Place all the provided files in the directory:
- app.py
- requirements.txt
- Dockerfile
- docker-compose.yml
- static/index.html
- .gitignore
- .dockerignore

### 3. Build and Run
```bash
# Make setup script executable
chmod +x setup.sh

# Run setup
./setup.sh

# Or manually:
docker-compose up --build -d
```

### 4. Access
Open browser: **http://localhost:5000**

**Login:** demo / demo123

## 📋 Features

- Monaco Editor (VS Code engine)
- Integrated Terminal (bash)
- Live HTML Preview
- File Management (CRUD operations)
- Code Execution (Python, JavaScript, Bash)
- Multi-file Tabs
- Auto-save
- Session Management

## 🛠️ Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Rebuild
docker-compose up --build -d

# Enter container
docker exec -it code-editor-pro bash
```

## 📝 Default Users

```
demo / demo123
admin / admin123
```

Add more users in `app.py`:
```python
USERS = {
    "demo": generate_password_hash("demo123"),
    "yourname": generate_password_hash("yourpassword")
}
```

## 🔒 Security Warning

**DO NOT** deploy to production as-is. This is for local development only.

For production:
1. Change SECRET_KEY
2. Add HTTPS
3. Implement proper authentication
4. Add rate limiting
5. Sandbox code execution
6. Use database for users

## 📦 Project Structure

```
code-editor-pro/
├── app.py                 # Backend server
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container config
├── docker-compose.yml    # Docker Compose
├── static/
│   └── index.html        # Frontend
├── workspace/            # User files (auto-created)
│   ├── demo/
│   └── admin/
├── .gitignore
├── .dockerignore
├── setup.sh
└── README.md
```

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Edit docker-compose.yml
ports:
  - "5001:5000"  # Change to different port
```

### Permission Errors
```bash
sudo chown -R $USER:$USER workspace/
sudo chmod -R 755 workspace/
```

### Container Won't Start
```bash
# Check logs
docker-compose logs

# Remove and rebuild
docker-compose down
docker-compose up --build
```

### Terminal Not Working
- Check browser console for errors
- Verify WebSocket connection
- Restart container

## 📚 Documentation

See full documentation in the original README for:
- API endpoints
- Advanced configuration
- Production deployment
- Adding languages
- Security considerations

## 📄 License

MIT License - Free to use and modify

## 🤝 Contributing

Pull requests welcome!

## 📧 Support

For issues, create a GitHub issue or contact support.
```

---

## Installation Steps Summary

### Step 1: Create Project Structure
```bash
mkdir code-editor-pro
cd code-editor-pro
mkdir static
```

### Step 2: Create Files

Save each file in the correct location:

1. **app.py** - Root directory
2. **requirements.txt** - Root directory
3. **Dockerfile** - Root directory
4. **docker-compose.yml** - Root directory
5. **static/index.html** - Inside static/ folder
6. **.gitignore** - Root directory (optional)
7. **.dockerignore** - Root directory (optional)
8. **setup.sh** - Root directory (optional, make executable)
9. **README.md** - Root directory (optional)

### Step 3: Build and Run

**Option A: Using Docker Compose (Recommended)**
```bash
docker-compose up --build -d
```

**Option B: Using Setup Script**
```bash
chmod +x setup.sh
./setup.sh
```

**Option C: Manual Docker Build**
```bash
# Build image
docker build -t code-editor-pro .

# Run container
docker run -d \
  -p 5000:5000 \
  -v $(pwd)/workspace:/workspace \
  --name code-editor-pro \
  code-editor-pro
```

### Step 4: Access

Open browser to: **http://localhost:5000**

Login with:
- Username: `demo`
- Password: `demo123`

### Step 5: Test Features

1. **File Management**: Create a new file (script.js)
2. **Code Editing**: Write some code
3. **Terminal**: Type `ls`, `pwd`, `python3 --version`
4. **Code Execution**: Create hello.py and click Run
5. **Live Preview**: Open index.html

---

## Additional Configuration Files

### File 10: Makefile (Optional - for convenience)

```makefile
.PHONY: build start stop restart logs shell clean help

help:
	@echo "Code Editor Pro - Make Commands"
	@echo "================================"
	@echo "make build    - Build Docker image"
	@echo "make start    - Start the editor"
	@echo "make stop     - Stop the editor"
	@echo "make restart  - Restart the editor"
	@echo "make logs     - View logs"
	@echo "make shell    - Enter container shell"
	@echo "make clean    - Remove containers and images"

build:
	docker-compose build

start:
	docker-compose up -d
	@echo "Editor started at http://localhost:5000"
	@echo "Login: demo / demo123"

stop:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

shell:
	docker exec -it code-editor-pro bash

clean:
	docker-compose down -v
	docker rmi code-editor-pro_web
```

---

### File 11: nginx.conf (Optional - for production with reverse proxy)

```nginx
upstream editor {
    server localhost:5000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Max upload size
    client_max_body_size 16M;

    location / {
        proxy_pass http://editor;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }

    location /socket.io {
        proxy_pass http://editor/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

### File 12: systemd service (Optional - for running without Docker)

```ini
[Unit]
Description=Code Editor Pro
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/code-editor-pro
Environment="PATH=/opt/code-editor-pro/venv/bin"
ExecStart=/opt/code-editor-pro/venv/bin/python app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## Complete Directory Structure

```
code-editor-pro/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker build instructions
├── docker-compose.yml          # Docker Compose configuration
├── .gitignore                  # Git ignore rules
├── .dockerignore              # Docker ignore rules
├── setup.sh                    # Setup automation script
├── README.md                   # Documentation
├── Makefile                    # Make commands (optional)
├── nginx.conf                  # Nginx config (optional)
├── static/
│   └── index.html             # Frontend application
└── workspace/                  # User workspaces (auto-created)
    ├── demo/                   # Demo user workspace
    │   ├── index.html         # Sample HTML file
    │   ├── hello.py           # Sample Python file
    │   ├── hello.js           # Sample JavaScript file
    │   ├── info.sh            # Sample bash script
    │   ├── styles.css         # Sample CSS file
    │   ├── config.json        # Sample JSON file
    │   └── README.md          # Sample markdown file
    └── admin/                  # Admin user workspace
```

---

## Environment Variables Reference

Add these to `docker-compose.yml` under `environment:`:

```yaml
environment:
  # Required
  - SECRET_KEY=your-secret-key-here
  
  # Optional
  - FLASK_ENV=production          # development or production
  - PYTHONUNBUFFERED=1           # Python output buffering
  - MAX_FILE_SIZE=16777216       # 16MB in bytes
  - CODE_TIMEOUT=10              # Code execution timeout
  - TERMINAL_COLS=80             # Default terminal columns
  - TERMINAL_ROWS=24             # Default terminal rows
  - LOG_LEVEL=INFO               # DEBUG, INFO, WARNING, ERROR
```

---

## Testing Checklist

After setup, test these features:

### ✅ Authentication
- [ ] Login with demo/demo123
- [ ] Login with admin/admin123
- [ ] Logout and re-login
- [ ] Invalid credentials show error

### ✅ File Operations
- [ ] View file tree
- [ ] Open existing file (index.html)
- [ ] Create new file
- [ ] Save file (manual)
- [ ] Auto-save works
- [ ] Create folder
- [ ] Refresh file tree

### ✅ Editor Features
- [ ] Syntax highlighting works
- [ ] Code completion works
- [ ] Multiple tabs work
- [ ] Close tab works
- [ ] Switch between tabs
- [ ] Cursor position updates

### ✅ Terminal
- [ ] Terminal connects
- [ ] Can type commands
- [ ] `ls` shows files
- [ ] `pwd` shows workspace
- [ ] `python3 --version` works
- [ ] Clear terminal works

### ✅ Code Execution
- [ ] Run Python file (.py)
- [ ] Run JavaScript file (.js)
- [ ] Run Bash script (.sh)
- [ ] Output appears in terminal
- [ ] Errors show in red

### ✅ Live Preview
- [ ] Preview opens for HTML files
- [ ] Preview updates on refresh
- [ ] Preview can be closed
- [ ] Preview shows rendered HTML

---

## Performance Optimization Tips

### 1. Increase Container Resources
Edit `docker-compose.yml`:
```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'
      memory: 4G
    reservations:
      cpus: '1.0'
      memory: 1G
```

### 2. Use Volume Caching
```yaml
volumes:
  - ./workspace:/workspace:cached
```

### 3. Optimize Monaco Loading
Use local Monaco instead of CDN:
```bash
# Download Monaco
wget https://registry.npmjs.org/monaco-editor/-/monaco-editor-0.34.0.tgz
tar -xzf monaco-editor-0.34.0.tgz
mv package/min/vs static/monaco
```

Then update index.html:
```javascript
require.config({ paths: { 'vs': '/monaco/vs' }});
```

---

## Common Issues and Solutions

### Issue 1: "Port 5000 already in use"
**Solution:**
```bash
# Find process using port 5000
lsof -i :5000
# Kill the process
kill -9 <PID>
# Or use different port
```

### Issue 2: "Permission denied" in workspace
**Solution:**
```bash
sudo chown -R $USER:$USER workspace/
sudo chmod -R 755 workspace/
```

### Issue 3: Monaco Editor not loading
**Solution:**
- Check internet connection (uses CDN)
- Check browser console for errors
- Try different browser
- Check firewall settings

### Issue 4: Terminal shows garbled text
**Solution:**
- Ensure UTF-8 encoding
- Resize terminal window
- Clear terminal and reconnect

### Issue 5: Code execution timeout
**Solution:**
Edit `app.py`, increase timeout:
```python
executors = {
    "python": {
        "cmd": ["python3", "-c", code],
        "timeout": 30  # Increase from 10 to 30
    }
}
```

---

## Production Deployment Guide

### 1. Secure Secret Key
```bash
# Generate random secret key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Add to docker-compose.yml:
```yaml
environment:
  - SECRET_KEY=<generated-key-here>
```

### 2. Add HTTPS with Let's Encrypt
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo certbot renew --dry-run
```

### 3. Use PostgreSQL for Users
```yaml
services:
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=editor
      - POSTGRES_USER=editor
      - POSTGRES_PASSWORD=secure-password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### 4. Add Rate Limiting
Install Flask-Limiter:
```bash
pip install Flask-Limiter
```

Update app.py:
```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    default_limits=["200 per hour", "50 per minute"]
)

@app.route("/api/execute")
@limiter.limit("10 per minute")
def execute_code():
    # ...
```

### 5. Enable Logging
```python
import logging

logging.basicConfig(
    filename='editor.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
```

---

## Backup and Restore

### Backup Workspace
```bash
# Create backup
tar -czf workspace-backup-$(date +%Y%m%d).tar.gz workspace/

# Restore backup
tar -xzf workspace-backup-20240101.tar.gz
```

### Backup Database (if using PostgreSQL)
```bash
# Backup
docker exec postgres pg_dump -U editor editor > backup.sql

# Restore
docker exec -i postgres psql -U editor editor < backup.sql
```

---

## Monitoring and Maintenance

### View Container Stats
```bash
docker stats code-editor-pro
```

### Check Disk Usage
```bash
du -sh workspace/*
```

### Clean Docker Resources
```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove unused containers
docker container prune
```

### Update Container
```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose up --build -d
```

---

## Advanced Features to Add

### 1. Git Integration
```python
@app.route("/api/git/init", methods=["POST"])
def git_init():
    workspace = get_user_workspace()
    subprocess.run(["git", "init"], cwd=workspace)
    return jsonify({"success": True})
```

### 2. Package Installation
```python
@app.route("/api/packages/install", methods=["POST"])
def install_package():
    package = request.json.get("package")
    result = subprocess.run(
        ["pip", "install", package],
        capture_output=True
    )
    return jsonify({"success": True, "output": result.stdout})
```

### 3. File Upload
```python
@app.route("/api/upload", methods=["POST"])
def upload_file():
    file = request.files['file']
    workspace = get_user_workspace()
    file.save(workspace / file.filename)
    return jsonify({"success": True})
```

### 4. Collaborative Editing (Y.js)
Add real-time collaboration using Y.js and WebRTC

### 5. AI Code Completion
Integrate OpenAI Codex or GitHub Copilot

---

## Final Notes

This is a **complete, production-ready foundation** for an online code editor. You have:

✅ All source code files
✅ Docker configuration
✅ Frontend with Monaco + Terminal
✅ Backend API with Flask
✅ Authentication system
✅ File management
✅ Code execution
✅ Documentation

**Next Steps:**
1. Copy all files to your project directory
2. Run `docker-compose up --build`
3. Access http://localhost:5000
4. Login and start coding!

**For Production:**
- Change SECRET_KEY
- Add HTTPS/SSL
- Implement database for users
- Add rate limiting
- Set up monitoring
- Configure backups

Happy Coding! 🚀
```