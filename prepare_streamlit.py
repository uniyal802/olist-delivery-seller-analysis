"""Package the validated dashboard snapshot for Streamlit without raw records."""
import gzip
import json
from pathlib import Path

root = Path(__file__).resolve().parent
html = (root / 'reports/dashboard.html').read_text(encoding='utf-8')
payload = html.split('const DATA=',1)[1].split(';\nconst $=',1)[0]
data = json.loads(payload)
assert sum(r['orders'] for r in data['monthly']) == data['overall']['all_orders']
assert sum(r['late'] for r in data['monthly']) == data['overall']['late_orders']
with gzip.open(root / 'reports/app_data.json.gz','wt',encoding='utf-8') as f:
    json.dump(data,f,separators=(',',':'))
print('Validated Streamlit snapshot created.')
