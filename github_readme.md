# 🚀 Code Editor Pro

A **web-based code editor** with Monaco Editor, integrated terminal, and live preview. Built with Flask and Docker.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)
![Python](https://img.shields.io/badge/Python-3.11-green.svg)

---

## ✨ Features

- 🎨 **Monaco Editor** - VS Code's powerful editor
- 💻 **Integrated Terminal** - Full bash shell with xterm.js
- 🌐 **Live HTML Preview** - Instant preview panel
- 📁 **File Management** - Create, edit, delete files and folders
- ▶️ **Code Execution** - Run Python, JavaScript, and Bash
- 🔐 **Authentication** - Secure login with isolated workspaces
- 🐳 **Docker Ready** - Complete containerization

---

## 🚀 Quick Start

```bash
# Clone repository
git clone https://github.com/yourusername/code-editor-pro.git
cd code-editor-pro

# Start with Docker Compose
docker-compose up --build -d

# Access at http://localhost:5000
# Login: demo / demo123
```

That's it! 🎉

---

## 📋 Requirements

- Docker & Docker Compose
- 2GB RAM minimum
- Port 5000 available

---

## 📖 Documentation

- **[Installation Guide](docs/INSTALLATION.md)** - Detailed setup instructions
- **[Usage Guide](docs/USAGE.md)** - How to use all features
- **[API Documentation](docs/API.md)** - Complete API reference
- **[Commands](docs/COMMANDS.md)** - All available commands
- **[Configuration](docs/CONFIGURATION.md)** - Environment variables and settings
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Production Deployment](docs/PRODUCTION.md)** - Security and deployment guide

---

## 🎯 Basic Usage

### Run Code
1. Create a Python/JavaScript/Bash file
2. Write your code
3. Click **▶️ Run** button
4. Output appears in terminal

### Use Terminal
```bash
# Navigate and create files
cd /workspace
touch myfile.py
nano myfile.py

# Install packages
pip install requests
npm install express

# Run commands
python3 script.py
node app.js
```

### Live Preview
1. Open an HTML file
2. Preview panel opens automatically
3. Edit and see changes instantly

---

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

---

## ⚙️ Configuration

Add users in `app.py`:
```python
USERS = {
    "demo": generate_password_hash("demo123"),
    "yourname": generate_password_hash("password123")
}
```

Change port in `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"  # Use port 8080
```

---

## 🔐 Security Warning

⚠️ **For local development only!** 

Before production:
- Change SECRET_KEY
- Add HTTPS
- Use database for users
- Implement rate limiting

See [Production Guide](docs/PRODUCTION.md) for details.

---

## 🐛 Troubleshooting

**Port already in use?**
```bash
# Change port in docker-compose.yml
ports: ["5001:5000"]
```

**Permission errors?**
```bash
sudo chown -R $USER:$USER workspace/
```

More solutions in [Troubleshooting Guide](docs/TROUBLESHOOTING.md)

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

1. Fork the repository
2. Create feature branch: `git checkout -b feature/amazing`
3. Commit changes: `git commit -m 'Add feature'`
4. Push: `git push origin feature/amazing`
5. Open Pull Request

---

## 📜 License

MIT License - see [LICENSE](LICENSE) file.

---

## 🙏 Credits

- [Monaco Editor](https://microsoft.github.io/monaco-editor/) - Microsoft
- [xterm.js](https://xtermjs.org/) - Terminal emulator
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Socket.IO](https://socket.io/) - Real-time communication

---

## 📞 Support

- 📖 [Documentation](docs/)
- 🐛 [Report Issues](https://github.com/yourusername/code-editor-pro/issues)
- 💬 [Discussions](https://github.com/yourusername/code-editor-pro/discussions)

---

<div align="center">

**Made with ❤️ for developers**

⭐ Star this repo if you find it helpful!

</div>