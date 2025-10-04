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