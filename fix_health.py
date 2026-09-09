import os

vm_host = os.environ.get("VM_HOST", "129.159.224.81")
vm_user = os.environ.get("VM_USER", "ubuntu")
vm_key = os.environ.get("VM_KEY", os.path.expanduser("~/.ssh/oci_key"))

import subprocess

def run(cmd):
    full = f"ssh -i {vm_key} -o StrictHostKeyChecking=no {vm_user}@{vm_host} {cmd!r}"
    return subprocess.run(full, shell=True, capture_output=True, text=True).stdout

# Write healthcheck script inside the container via docker exec
# First check if container is running
status = run("docker ps --format '{{.Names}} {{.Status}}' | grep backend || echo 'no backend'")
print("Backend status:", status.strip())

# Create healthcheck script on the host that will be copied into container
script = '''import urllib.request
import sys
try:
    r = urllib.request.urlopen("http://localhost:8000/api/v1/health", timeout=5)
    sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
'''

# Write script to host temp
with open("/tmp/healthcheck.py", "w") as f:
    f.write(script)

# Copy into container
run("docker cp /tmp/healthcheck.py tradingai-backend-1:/opt/tradingai/healthcheck.py 2>&1")

# Also fix the docker-compose to use a simple one-liner
compose_fix = '''    healthcheck:
      test: ["CMD", "python3", "-c", "import urllib.request; r=urllib.request.urlopen(\\"http://localhost:8000/api/v1/health\\", timeout=5); exit(0 if r.status==200 else 1)"]
      interval: 30s
      timeout: 10s
      retries: 3'''

print("Healthcheck script copied into container")
print("Now restart backend with: docker compose -f docker-compose.vm.yml up -d backend")
