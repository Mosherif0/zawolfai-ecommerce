import requests
import json

base = 'http://127.0.0.1:8000'

# Test health (fast)
h = requests.get(base + '/health', timeout=5)
print('HEALTH:', h.status_code, h.json())

# Test index page (fast)
r = requests.get(base + '/', timeout=5)
print('INDEX:', r.status_code, r.headers.get('content-type', '')[:40])



