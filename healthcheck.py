import urllib.request
import sys
try:
    r = urllib.request.urlopen("http://localhost:8000/api/v1/health", timeout=5)
    sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)