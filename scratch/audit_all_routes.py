import os
import re

# 1. Collect all routes registered in FastAPI routers
routes = set()

router_files = [
    'sar/src/api/routers/docs_router.py',
    'sar/src/api/routers/ops_router.py',
    'sar/src/api/routers/admin_router.py',
    'sar/src/api/routers/security_router.py'
]

prefix_map = {
    'docs_router.py': '/api/docs',
    'ops_router.py': '/api/ops',
    'admin_router.py': '/api/admin',
    'security_router.py': '/api/auth'
}

for rf in router_files:
    fname = os.path.basename(rf)
    pfx = prefix_map.get(fname, '')
    with open(rf, encoding='utf-8') as f:
        content = f.read()
    for m, p in re.findall(r'@router\.(get|post|put|delete|patch)\(\s*["\']([^"\']+)["\']', content):
        full_route = (m.upper(), f"{pfx.rstrip('/')}/{p.lstrip('/')}")
        routes.add(full_route)

print(f"Total backend routes found: {len(routes)}")

# 2. Collect all api_client.request calls across the UI and services
ui_dirs = ['sar/src/ui', 'sar/src/services', 'sar/src/storage']
calls = []

for udir in ui_dirs:
    for root, dirs, files in os.walk(udir):
        for file in files:
            if file.endswith('.py'):
                fp = os.path.join(root, file)
                with open(fp, encoding='utf-8') as f:
                    txt = f.read()
                matches = re.findall(r'api_client\.request\(\s*["\'](\w+)["\'],\s*(f?["\'][^"\']+["\'])', txt)
                for m, rp in matches:
                    p = rp.strip('f"\'')
                    calls.append((fp, m.upper(), p))

print(f"Total API client calls found: {len(calls)}")

def match_route(call_method, call_path):
    for r_method, r_path in routes:
        if call_method != r_method:
            continue
        # Convert {var} to regex pattern [^/]+
        pattern = '^' + re.sub(r'\{[^}]+\}', r'[^/]+', r_path) + '$'
        # Also normalize any client-side f-string like {usuario_id} to test value e.g. 1
        test_path = re.sub(r'\{[^}]+\}', '1', call_path)
        if re.match(pattern, test_path) or r_path == call_path:
            return True
    return False

missing = []
for fp, m, p in calls:
    if not match_route(m, p):
        missing.append((fp, m, p))
        print(f"MISSING 404: [{m}] {p} in {fp}")

if not missing:
    print("ALL API CALLS MATCH REGISTERED FASTAPI ROUTES!")
else:
    print(f"Found {len(missing)} missing route(s)!")
