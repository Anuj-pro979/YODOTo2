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