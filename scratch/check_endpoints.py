import re

with open('sar/src/services/inventario_ui_service.py', encoding='utf-8') as f:
    ui_content = f.read()

with open('sar/src/api/routers/docs_router.py', encoding='utf-8') as f:
    router_content = f.read()

# Find all endpoints in inventario_ui_service.py
calls = re.findall(r'api_client\.request\(\s*["\'](\w+)["\'],\s*(f?["\'][^"\']+["\'])', ui_content)
print(f'Total endpoints called in inventario_ui_service: {len(calls)}')

for method, raw_path in calls:
    path = raw_path.strip('f"\'')
    subpath = path.replace('/api/docs', '')
    # regex for {var}
    pattern = re.sub(r'\{[^}]+\}', r'\{[^}]+\}', re.escape(subpath))
    pattern = pattern.replace(r'\{[^}]+\}', r'\{[^}]+\}')
    
    found = False
    for line in router_content.splitlines():
        if '@router.' in line and subpath in line:
            found = True
            break
        elif '@router.' in line:
            # check normalized matching
            r_norm = re.sub(r'\{[^}]+\}', '{param}', line)
            s_norm = re.sub(r'\{[^}]+\}', '{param}', subpath)
            if s_norm in r_norm:
                found = True
                break
    status = 'FOUND' if found else '*** MISSING 404! ***'
    print(f'{method:6} {path:50} -> {status}')
