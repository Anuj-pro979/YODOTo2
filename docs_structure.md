# 📚 Documentation Files Structure

Create a `docs/` folder and add these files:

---

## File 1: docs/INSTALLATION.md

```markdown
# Installation Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum
- Port 5000 available

## Method 1: Docker Compose (Recommended)

```bash
git clone https://github.com/yourusername/code-editor-pro.git
cd code-editor-pro
docker-compose up --build -d
```

Access at: http://localhost:5000

## Method 2: Using Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

## Method 3: Manual Docker

```bash
docker build -t code-editor-pro .
docker run -d -p 5000:5000 -v $(pwd)/workspace:/workspace code-editor-pro
```

## Platform-Specific Setup

### Ubuntu/Debian
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

### macOS
```bash
brew install --cask docker
```

### Windows
Download Docker Desktop from docker.com

## Verification

```bash
docker ps
# Should show code-editor-pro container running
```

## Default Login

- Username: `demo`
- Password: `demo123`
```

---

## File 2: docs/USAGE.md

```markdown
# Usage Guide

## Login

1. Open http://localhost:5000
2. Username: `demo`
3. Password: `demo123`

## Creating Files

1. Click **📄 New** in sidebar
2. Enter filename: `script.py`
3. Start coding

## Running Code

### Python
```python
print("Hello, World!")
```
Click **▶️ Run**

### JavaScript
```javascript
console.log("Hello, World!");
```
Click **▶️ Run**

### Bash
```bash
echo "Hello, World!"
ls -la
```
Click **▶️ Run**

## Using Terminal

```bash
cd /workspace
touch myfile.py
nano myfile.py
python3 myfile.py
```

## Live Preview

1. Create `index.html`
2. Write HTML
3. Preview opens automatically
4. Click **🔄 Preview** to refresh

## Keyboard Shortcuts

- `Ctrl+S` - Save
- `Ctrl+F` - Find
- `Ctrl+/` - Comment
- `Alt+↑↓` - Move line
```

---

## File 3: docs/API.md

```markdown
# API Documentation

Base URL: `http://localhost:5000/api`

## Authentication

### POST /auth/login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"demo","password":"demo123"}'
```

### POST /auth/logout
```bash
curl -X POST http://localhost:5000/api/auth/logout
```

## File Operations

### GET /files
List all files
```bash
curl http://localhost:5000/api/files
```

### GET /files/{path}
Read file content
```bash
curl http://localhost:5000/api/files/index.html
```

### POST /files/{path}
Create/update file
```bash
curl -X POST http://localhost:5000/api/files/test.py \
  -H "Content-Type: application/json" \
  -d '{"content":"print(\"hello\")"}'
```

### DELETE /files/{path}
Delete file
```bash
curl -X DELETE http://localhost:5000/api/files/test.py
```

## Code Execution

### POST /execute
```bash
curl -X POST http://localhost:5000/api/execute \
  -H "Content-Type: application/json" \
  -d '{"code":"print(\"test\")", "language":"python"}'
```

## WebSocket Events

### Connect to Terminal
```javascript
socket.emit('terminal.connect');
```

### Send Input
```javascript
socket.emit('terminal.input', {input: 'ls\n'});
```

### Receive Output
```javascript
socket.on('terminal.output', (data) => {
  console.log(data.output);
});
```
```

---

## File 4: docs/COMMANDS.md

```markdown
# Commands Reference

## Docker Commands

```bash
# Start
docker-compose up -d

# Stop
docker-compose down

# Rebuild
docker-compose up --build -d

# View logs
docker-compose logs -f

# Restart
docker-compose restart

# Enter container
docker exec -it code-editor-pro bash

# Stats
docker stats code-editor-pro
```

## Terminal Commands (Inside Editor)

```bash
# File operations
touch file.txt
mkdir folder
rm file.txt
cp file.txt backup.txt
mv old.txt new.txt

# Python
python3 script.py
pip install requests
pip list

# JavaScript
node script.js
npm install express
npm list

# Git
git init
git add .
git commit -m "message"
git status

# System
pwd
ls -la
df -h
ps aux
```

## Maintenance

```bash
# Backup
tar -czf backup.tar.gz workspace/

# Restore
tar -xzf backup.tar.gz

# Clean Docker
docker system prune -a

# Fix permissions
sudo chown -R $USER:$USER workspace/
```
```

---

## File 5: docs/CONFIGURATION.md

```markdown
# Configuration Guide

## Environment Variables

Edit `docker-compose.yml`:

```yaml
environment:
  - SECRET_KEY=your-secret-key
  - FLASK_ENV=production
  - CODE_TIMEOUT=10
  - MAX_FILE_SIZE=16777216
```

## Adding Users

Edit `app.py`:

```python
USERS = {
    "demo": generate_password_hash("demo123"),
    "john": generate_password_hash("john123"),
}
```

Generate hash:
```bash
python3 -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('password'))"
```

## Change Port

Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:5000"
```

## Resource Limits

```yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
```

## Add Languages

Edit `app.py`:
```python
executors = {
    "python": {"cmd": ["python3", "-c", code], "timeout": 10},
    "ruby": {"cmd": ["ruby", "-e", code], "timeout": 10},
}
```

Update `Dockerfile`:
```dockerfile
RUN apt-get install -y ruby
```
```

---

## File 6: docs/TROUBLESHOOTING.md

```markdown
# Troubleshooting Guide

## Port Already in Use

**Error:** `bind: address already in use`

**Solution:**
```bash
# Find process
lsof -i :5000

# Kill it
kill -9 <PID>

# Or change port
# Edit docker-compose.yml: ports: ["5001:5000"]
```

## Permission Denied

**Error:** `Permission denied` in workspace

**Solution:**
```bash
sudo chown -R $USER:$USER workspace/
sudo chmod -R 755 workspace/
```

## Monaco Not Loading

**Error:** Editor shows blank

**Solution:**
- Check internet connection (uses CDN)
- Check browser console
- Try incognito mode
- Clear browser cache

## Terminal Not Working

**Error:** Terminal shows `[Disconnected]`

**Solution:**
```bash
# Check logs
docker-compose logs -f

# Restart
docker-compose restart

# Check WebSocket in browser console
```

## Container Won't Start

**Solution:**
```bash
# View logs
docker-compose logs

# Remove and rebuild
docker-compose down -v
docker-compose up --build
```

## Code Execution Timeout

**Solution:**
Increase timeout in `app.py`:
```python
"timeout": 30  # Change from 10
```

## Out of Disk Space

**Solution:**
```bash
# Check usage
df -h
du -sh workspace/*

# Clean Docker
docker system prune -a
docker volume prune
```
```

---

## File 7: docs/PRODUCTION.md

```markdown
# Production Deployment Guide

## ⚠️ Security Checklist

- [ ] Change SECRET_KEY
- [ ] Enable HTTPS
- [ ] Use database for users
- [ ] Add rate limiting
- [ ] Set up logging
- [ ] Configure firewall
- [ ] Regular backups

## 1. Secret Key

```bash
# Generate secure key
python3 -c "import secrets; print(secrets.token_hex(32))"

# Add to docker-compose.yml
environment:
  - SECRET_KEY=<generated-key>
```

## 2. HTTPS with Nginx

Install Certbot:
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

Nginx config:
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 3. PostgreSQL Database

Add to `docker-compose.yml`:
```yaml
services:
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: editor
      POSTGRES_USER: editor
      POSTGRES_PASSWORD: secure-password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 4. Rate Limiting

Install:
```bash
pip install Flask-Limiter
```

Add to `app.py`:
```python
from flask_limiter import Limiter

limiter = Limiter(app, default_limits=["200/hour"])
```

## 5. Logging

```python
import logging

logging.basicConfig(
    filename='editor.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s'
)
```

## 6. Firewall

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## 7. Backup Script

```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d)
tar -czf backup-$DATE.tar.gz workspace/
# Upload to S3 or backup server
```

## Monitoring

Use Prometheus + Grafana:
```yaml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
```
```

---

## File 8: CONTRIBUTING.md (Root folder)

```markdown
# Contributing Guidelines

Thank you for contributing! 🎉

## How to Contribute

1. Fork the repository
2. Create branch: `git checkout -b feature/amazing`
3. Make changes
4. Test thoroughly
5. Commit: `git commit -m 'Add feature'`
6. Push: `git push origin feature/amazing`
7. Open Pull Request

## Code Style

### Python
- Follow PEP 8
- Use type hints
- Add docstrings

### JavaScript
- Use ES6+
- Use const/let
- Add comments

## Testing

Test your changes:
```bash
docker-compose up --build -d
# Test all features
```

## Commit Messages

Use clear commit messages:
- ✨ `feat: add new feature`
- 🐛 `fix: resolve bug`
- 📝 `docs: update documentation`
- 🎨 `style: format code`
- ♻️ `refactor: restructure code`

## Pull Request Guidelines

- Link related issues
- Describe changes clearly
- Add screenshots if UI changes
- Update documentation
- Ensure tests pass

## Reporting Bugs

Include:
- Clear title
- Steps to reproduce
- Expected behavior
- Actual behavior
- Screenshots
- System info

## Questions?

Open a discussion or issue!
```

---

## Summary

Your documentation structure:

```
project/
├── README.md (short, focused)
├── CONTRIBUTING.md
├── LICENSE
└── docs/
    ├── INSTALLATION.md
    ├── USAGE.md
    ├── API.md
    ├── COMMANDS.md
    ├── CONFIGURATION.md
    ├── TROUBLESHOOTING.md
    └── PRODUCTION.md
```

**Benefits:**
- ✅ Clean, short README
- ✅ Easy to navigate
- ✅ Focused documentation
- ✅ Professional structure
- ✅ Easy to maintain
