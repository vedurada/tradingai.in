#!/usr/bin/env bash
set -euo pipefail

VM_USER="ubuntu"
VM_HOST="129.159.224.81"
SSH_KEY="$HOME/.ssh/oci_key"
PROJECT_DIR="/opt/tradingai"

echo "=== TradingAI VM Deployment Script ==="
echo "Target: $VM_USER@$VM_HOST"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_HOST" 'bash -s' << 'REMOTE_SCRIPT'
set -euo pipefail

echo "--- Step 1: Install Docker ---"
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo usermod -aG docker "$USER"
echo "Docker installed: $(docker --version)"

echo "--- Step 2: Install Nginx ---"
sudo apt-get install -y nginx
sudo systemctl enable nginx
sudo systemctl start nginx
echo "Nginx installed: $(nginx -v 2>&1)"

echo "--- Step 3: Create project directory ---"
sudo mkdir -p /opt/tradingai
sudo chown "$USER":"$USER" /opt/tradingai
echo "Project dir ready"

echo "--- Step 4: Deploy Docker Compose ---"
mkdir -p ~/tradingai-deploy
cat > ~/tradingai-deploy/docker-compose.yml << 'EOF'
version: "3.9"

services:
  frontend:
    build:
      context: ./docker/frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

  backend:
    build:
      context: ./docker/backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - DEBUG=false
      - DB_HOST=postgres
      - DB_PORT=5432
      - DB_NAME=tradingai
      - DB_USER=tradingai
      - DB_PASSWORD=tradingai
      - REDIS_HOST=redis
      - REDIS_PORT=6379
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: tradingai
      POSTGRES_USER: tradingai
      POSTGRES_PASSWORD: tradingai
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./data/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    ports:
      - "127.0.0.1:5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tradingai -d tradingai"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "127.0.0.1:6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
EOF

echo "--- Step 5: Create Nginx config ---"
mkdir -p ~/tradingai-deploy/nginx
cat > ~/tradingai-deploy/nginx/tradingai.conf << 'EOF'
server {
    listen 80;
    server_name tradingai.in www.tradingai.in;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

echo "--- Step 6: Copy project files ---"
# The project files will be copied separately via rsync/scp
echo "Ready for project files"

echo "--- Step 7: Setup complete ---"
echo "Run the following to complete deployment:"
echo "  1. rsync -avz tradingai/ ubuntu@129.159.224.81:~/tradingai-deploy/"
echo "  2. ssh ubuntu@129.159.224.81"
echo "  3. cd ~/tradingai-deploy && docker compose up -d"
echo "  4. sudo ln -sf ~/tradingai-deploy/nginx/tradingai.conf /etc/nginx/sites-available/tradingai"
echo "  5. sudo ln -sf /etc/nginx/sites-available/tradingai /etc/nginx/sites-enabled/"
echo "  6. sudo rm -f /etc/nginx/sites-enabled/default"
echo "  7. sudo systemctl reload nginx"

REMOTE_SCRIPT