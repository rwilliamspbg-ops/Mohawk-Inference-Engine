# Mohawk Inference Engine - Production Deployment Guide v2.1.0

Complete guide for deploying the Mohawk Inference Engine GUI to production environments on Windows, Linux, and macOS.

---

## 📋 Table of Contents

1. [Quick Deploy Options](#quick-deploy-options)
2. [Windows Deployment](#windows-deployment)
3. [Linux Deployment](#linux-deployment)
4. [macOS Deployment](#macos-deployment)
5. [Docker Deployment](#docker-deployment)
6. [Cloud Deployment](#cloud-deployment)
7. [Security Hardening](#security-hardening)
8. [Monitoring & Logging](#monitoring--logging)
9. [Troubleshooting](#troubleshooting)

---

## 🚀 Quick Deploy Options

### Option 1: Single Executable (Fastest)

**Windows:**
```bash
build_windows.bat
copy dist\Mohawk*-Inference-Engine.exe C:\Program Files\Mohawk\
C:\Program Files\Mohawk\Mohawk-Inference-Engine.exe --host localhost --port 8003
```

**Linux:**
```bash
./build_linux.sh
cp dist/Mohawk*-Inference-Engine /usr/local/bin/
Mohawk-Inference-Engine --host localhost --port 8003
```

### Option 2: Docker Container (Recommended for Production)

```bash
docker-compose up -d
```

### Option 3: Python Package (Development/Testing)

```bash
pip install .
mohawk-gui --host localhost --port 8003
```

---

## 🪟 Windows Deployment

### Prerequisites

- Windows 10/11 (64-bit)
- Python 3.10+ installed
- NVIDIA GPU drivers (for GPU inference)
- Docker Desktop (optional, for containerized deployment)

### Step-by-Step Deployment

#### 1. Install Dependencies

```bash
# Clone or navigate to repository
cd C:\Users\rwill\Mohawk-Inference-Engine

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install production dependencies
pip install -r requirements.txt
```

#### 2. Generate Authentication Key

```bash
mkdir -p certs
python mohawk_gui/main.py --key-file certs/auth_key.pem
```

#### 3. Build Executable

```bash
build_windows.bat
```

The executable will be created at `dist\Mohawk*-Inference-Engine.exe`

#### 4. Deploy to Production Location

```bash
# Create installation directory
mkdir C:\Program Files\Mohawk

# Copy executable
copy dist\Mohawk*-Inference-Engine.exe "C:\Program Files\Mohawk\Mohawk-Inference-Engine.exe"

# Copy resources if needed
xcopy mohawk_gui\resources "C:\Program Files\Mohawk\resources\" /E /I /Y

# Create logs directory
mkdir C:\Program Files\Mohawk\logs
```

#### 5. Create Desktop Shortcut

```powershell
# Create shortcut
$shortcut = [System.Windows.Shell.ApplicationActivationState]::Active
Add-AppxPackage -Path "C:\Program Files\Mohawk\Mohawk-Inference-Engine.exe"
```

Or manually create shortcut:
1. Right-click on Desktop → New → Shortcut
2. Browse to `C:\Program Files\Mohawk\Mohawk-Inference-Engine.exe`
3. Add arguments: `--host localhost --port 8003`

#### 6. Configure Firewall

```powershell
# Allow GUI through firewall
New-NetFirewallRule -DisplayName "Mohawk Inference Engine GUI" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8003,8443 `
    -Action Allow
```

### Windows Service Installation (Optional)

Create `C:\Program Files\Mohawk\MohawkService.svc`:

```powershell
@echo off
REM Mohawk Inference Engine Windows Service
set MOHAWK_INSTALL_DIR=C:\Program Files\Mohawk
set MOHAWK_EXE=%MOHAWK_INSTALL_DIR%\Mohawk-Inference-Engine.exe
set MOHAWK_LOGS=%MOHAWK_INSTALL_DIR%\logs

%MOHAWK_EXE% --host 0.0.0.0 --port 8003 > %MOHAWK_LOGS\service.log 2>&1
```

Register as Windows Service:

```powershell
sc create MohawkInference binPath="C:\Program Files\Mohawk\MohawkService.svc" start=auto
sc start MohawkInference
```

---

## 🐧 Linux Deployment

### Prerequisites

- Ubuntu 20.04/22.04 LTS or RHEL/CentOS 8+
- Python 3.10+ installed
- NVIDIA drivers (for GPU inference)
- Docker (optional, for containerized deployment)

### Step-by-Step Deployment

#### 1. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3.11 \
    python3.11-venv \
    python3-pip \
    libgl1-mesa-glx \
    libxkbcommon-x11-0 \
    libdbus-1-3

# Create project directory
mkdir -p /opt/mohawk
cd /opt/mohawk

# Clone or copy repository
git clone https://github.com/your-org/mohawk-inference-engine.git .

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install production dependencies
pip install -r requirements.txt
```

#### 2. Generate Authentication Key

```bash
mkdir -p /opt/mohawk/certs
python mohawk_gui/main.py --key-file certs/auth_key.pem
```

#### 3. Build Executable

```bash
./build_linux.sh
```

The executable will be created at `dist/Mohawk*-Inference-Engine`

#### 4. Deploy to System

```bash
# Copy executable to system path
sudo cp dist/Mohawk*-Inference-Engine /usr/local/bin/

# Make it executable
sudo chmod +x /usr/local/bin/Mohawk-Inference-Engine

# Create logs directory
sudo mkdir -p /var/log/mohawk
sudo chown root:root /var/log/mohawk
```

#### 5. Configure Systemd Service

Create `/etc/systemd/system/mohawk-gui.service`:

```ini
[Unit]
Description=Mohawk Inference Engine GUI
After=network.target nvidia-driver.service

[Service]
Type=simple
User=mohawk
Group=mohawk
WorkingDirectory=/opt/mohawk
Environment="PYTHONPATH=/opt/mohawk"
ExecStart=/opt/mohawk/venv/bin/python /opt/mohawk/dist/Mohawk-Inference-Engine \
    --host 0.0.0.0 \
    --port 8003 \
    --key-file /opt/mohawk/certs/auth_key.pem
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

#### 6. Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable mohawk-gui
sudo systemctl start mohawk-gui

# Check status
sudo systemctl status mohawk-gui

# View logs
sudo journalctl -u mohawk-gui -f
```

#### 7. Configure Firewall (UFW)

```bash
sudo ufw allow 8003/tcp
sudo ufw allow 8443/tcp
```

---

## 🍎 macOS Deployment

### Prerequisites

- macOS 12+ (Monterey or later)
- Python 3.10+ installed
- Docker Desktop for Mac (optional)

### Step-by-Step Deployment

#### 1. Install Dependencies

```bash
# Create project directory
mkdir -p ~/Projects/mohawk-inference-engine
cd ~/Projects/mohawk-inference-engine

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install production dependencies
pip install -r requirements.txt
```

#### 2. Generate Authentication Key

```bash
mkdir -p certs
python mohawk_gui/main.py --key-file certs/auth_key.pem
```

#### 3. Build Executable

```bash
./build_linux.sh  # Works on macOS too, or use pyinstaller directly
```

#### 4. Deploy to Applications Folder

```bash
cp dist/Mohawk*-Inference-Engine ~/Applications/
chmod +x ~/Applications/Mohawk-Inference-Engine
ln -s ~/Applications/Mohawk-Inference-Engine /Applications/Mohawk\ Inference\ Engine.app
```

#### 5. Configure Login Items (Auto-start)

```bash
# Add to login items
defaults write com.apple.loginitems Automate -array \
    "/Applications/Mohawk Inference Engine.app"
defaults write com.apple.loginitems EnableRunningApps -bool true
```

---

## 🐳 Docker Deployment (Cross-platform)

### Quick Start

```bash
# Build and run both GUI and worker
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f mohawk-gui
```

### Custom Docker Image

```bash
# Build custom image
docker build -t mohawk-gui:latest .

# Run with custom configuration
docker run -d \
    --name mohawk-gui \
    --gpus all \
    -p 8003:8003 \
    -p 8443:8443 \
    -v $(pwd)/certs:/app/certs:ro \
    -v $(pwd)/logs:/app/logs \
    -e HOST=0.0.0.0 \
    -e PORT=8003 \
    -e SSL_ENABLED=true \
    mohawk-gui:latest
```

### Kubernetes Deployment (Optional)

Create `kubernetes/mohawk-gui-deployment.yaml`:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mohawk-gui
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mohawk-gui
  template:
    metadata:
      labels:
        app: mohawk-gui
    spec:
      containers:
      - name: mohawk-gui
        image: your-registry/mohawk-gui:latest
        ports:
        - containerPort: 8003
        - containerPort: 8443
        env:
        - name: HOST
          value: "0.0.0.0"
        - name: PORT
          value: "8003"
        volumeMounts:
        - name: certs
          mountPath: /app/certs
        - name: logs
          mountPath: /app/logs
      volumes:
      - name: certs
        hostPath:
          path: /path/to/certs
          type: Directory
      - name: logs
        emptyDir: {}
```

---

## ☁️ Cloud Deployment

### AWS EC2

```bash
# Launch EC2 instance with Ubuntu 22.04
# Security group: Allow ports 8003, 8443

# Connect via SSH
ssh -i your-key.pem ec2-user@your-instance-ip

# Deploy (follow Linux deployment steps above)
./build_linux.sh
sudo systemctl start mohawk-gui
```

### AWS ECS (Elastic Container Service)

```bash
# Build Docker image
docker build -t mohawk-gui:latest .

# Push to ECR
aws ecr create-repository --repository-name mohawk-gui
aws ecr get-login-password | docker login --username AWS --password-stdin <account-id>.dkr.ecr.<region>.amazonaws.com
docker push <account-id>.dkr.ecr.<region>.amazonaws.com/mohawk-gui:latest

# Create ECS task definition and service
# Configure with Fargate or EC2 launch type
```

### Azure VM

```bash
# Launch Azure VM with Ubuntu 22.04
# Deploy using Linux deployment steps

# Or use Azure Container Instances
az container create \
    --name mohawk-gui \
    --resource-group myResourceGroup \
    --image your-registry/mohawk-gui:latest \
    --dns-name-label mohawk-gui \
    --ports 8003 8443
```

### Google Cloud Run

```bash
# Build and push to Container Registry
gcr.io/cloud-builders/docker build -t gcr.io/PROJECT_ID/mohawk-gui:latest .
gcloud containers images push gcr.io/PROJECT_ID/mohawk-gui:latest

# Deploy to Cloud Run
gcloud run deploy mohawk-gui \
    --image gcr.io/PROJECT_ID/mohawk-gui:latest \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated
```

---

## 🔒 Security Hardening

### 1. Enable SSL/TLS

```bash
# Generate self-signed certificates (for testing)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout certs/server.key \
    -out certs/server.crt \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Or use Let's Encrypt for production
certbot certonly --standalone -d your-domain.com
```

### 2. Configure Firewall Rules

**Linux (ufw):**
```bash
sudo ufw deny 8003/tcp  # Deny by default
sudo ufw allow from 10.0.0.0/8 to any port 8003 proto tcp  # Allow internal only
sudo ufw allow from your-ip to any port 8003 proto tcp  # Allow specific IP
```

**Windows:**
```powershell
# Only allow trusted IPs
New-NetFirewallRule -DisplayName "Mohawk Inference Engine" `
    -Direction Inbound `
    -Protocol TCP `
    -LocalPort 8003 `
    -Action Allow `
    -RemoteAddress 10.0.0.0/8
```

### 3. Configure Non-Root User (Linux)

```ini
# In systemd service file
User=mohawk
Group=mohawk
```

### 4. Enable Audit Logging

Edit `config.toml`:
```toml
[logging]
level = "INFO"
file = "/var/log/mohawk/audit.log"
format = "json"

[security]
audit_enabled = true
```

### 5. Regular Security Updates

```bash
# Linux: Update system and dependencies
sudo apt update && sudo apt upgrade -y

# Check for vulnerabilities
pip install safety
safety check --full-report
```

---

## 📊 Monitoring & Logging

### Application Logs

**Linux:**
```bash
# View logs
sudo tail -f /var/log/mohawk/mohawk_gui.log

# Or use journalctl
sudo journalctl -u mohawk-gui -f
```

**Windows:**
```powershell
Get-Content "C:\Program Files\Mohawk\logs\mohawk_gui.log" -Tail -Wait
```

### Docker Logs

```bash
docker-compose logs -f mohawk-gui
```

### Prometheus Metrics (Optional)

Add to `config.toml`:
```toml
[metrics]
export_interval_s = 60
enable_prometheus = true
prometheus_port = 9090
```

### Grafana Dashboard Integration

Configure metrics endpoint and add Grafana dashboard for visualization.

---

## 🔧 Troubleshooting

### Common Issues

#### Issue: "ImportError: No module named mohawk_gui"

**Solution:**
```bash
# Linux
source venv/bin/activate
pip install -e .

# Or reinstall
pip install -r requirements.txt
```

#### Issue: "PyQt6: Could not load the Qt platform plugin"

**Solution:**
```bash
# Install system dependencies
sudo apt install libgl1-mesa-glx libxkbcommon-x11-0 libdbus-1-3

# Or for Windows, ensure OpenGL drivers are installed
```

#### Issue: "CUDA error: no CUDA-capable device"

**Solution:**
```bash
# Check GPU detection
nvidia-smi

# Install CUDA-enabled dependencies
pip install torch --index-url https://download.pytorch.org/whl/cu118
```

#### Issue: Docker container won't start

**Solution:**
```bash
# Check logs
docker-compose logs mohawk-gui

# Ensure GPU drivers are installed
nvidia-smi

# Rebuild image
docker-compose build --no-cache
```

### Debug Mode

Run with verbose logging:
```bash
python mohawk_gui/main.py --host localhost --port 8003 --log-level DEBUG
```

---

## ✅ Deployment Checklist

Before deploying to production:

- [ ] Generate authentication key (`certs/auth_key.pem`)
- [ ] Configure SSL/TLS certificates (production)
- [ ] Set up firewall rules (allow only trusted IPs)
- [ ] Configure systemd service (Linux) or Windows service
- [ ] Enable audit logging
- [ ] Test connection to worker endpoints
- [ ] Verify GPU detection (`nvidia-smi`)
- [ ] Check memory and CPU resources
- [ ] Set up monitoring and alerting
- [ ] Document deployment configuration

---

## 📞 Support

For deployment issues:
1. Check logs: `journalctl -u mohawk-gui -f` (Linux) or event viewer (Windows)
2. Review documentation in repository
3. Open issue on GitHub with error details

---

**Mohawk Inference Engine v2.1.0 - Production Deployment Ready!** 🚀
