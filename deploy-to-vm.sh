#!/usr/bin/env bash
set -euo pipefail

VM_USER="ubuntu"
VM_HOST="129.159.224.81"
SSH_KEY="$HOME/.ssh/oci_key"
PROJECT_DIR="/opt/tradingai"

echo "=== Deploying TradingAI to VM ==="

# Create project directory on VM
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_HOST" "mkdir -p $PROJECT_DIR"

# Copy project files (exclude node_modules, .next, __pycache__, .git)
echo "Copying project files..."
rsync -avz --delete \
  --exclude='node_modules' \
  --exclude='.next' \
  --exclude='__pycache__' \
  --exclude='.pytest_cache' \
  --exclude='.git' \
  --exclude='logs' \
  --exclude='deploy-vm.sh' \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  /Users/satya/remove_workspace/tradingai/ \
  "$VM_USER@$VM_HOST:$PROJECT_DIR/"

echo "Files copied successfully"

# Run setup on VM
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$VM_USER@$VM_HOST" 'bash -s' << 'REMOTE_SCRIPT'
set -euo pipefail
PROJECT_DIR="/opt/tradingai"
cd "$PROJECT_DIR"

echo "--- Setting up backend ---"
pip3 install -r backend/requirements.txt 2>&1 | tail -3 || echo "pip install skipped (will use Docker)"

echo "--- Setting up Nginx config ---"
sudo mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled
cat > ~/tradingai.nginx.conf << 'NGINX'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX
sudo cp ~/tradingai.nginx.conf /etc/nginx/sites-available/tradingai
sudo ln -sf /etc/nginx/sites-available/tradingai /etc/nginx/sites-enabled/tradingai
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t 2>&1
sudo systemctl reload nginx 2>&1 || sudo systemctl start nginx 2>&1

echo "--- Starting Docker containers ---"
docker compose up -d --build 2>&1

echo "--- Waiting for services ---"
sleep 15

echo "--- Checking services ---"
docker compose ps 2>&1

echo "--- Testing endpoints ---"
curl -s http://localhost:8000/api/v1/health 2>&1 || echo "Backend not ready yet"
curl -s -o /dev/null -w "Frontend HTTP: %{http_code}\n" http://localhost:3000/ 2>&1 || echo "Frontend not ready yet"

echo "=== Deployment complete ==="
echo "Frontend: http://129.159.224.81"
echo "Backend API: http://129.159.224.81/api/v1/health"
REMOTE_SCRIPT