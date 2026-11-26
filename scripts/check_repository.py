"""Offline structure, syntax, translation and PNG checks (not Hassfest)."""
import ast
import json
from pathlib import Path
import struct
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'custom_components/bkw_dynamic_tariffs'

for path in ROOT.rglob('*.py'):
    ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
for path in ROOT.rglob('*.json'):
    json.loads(path.read_text(encoding='utf-8'))
manifest=json.loads((C/'manifest.json').read_text())
hacs=json.loads((ROOT/'hacs.json').read_text())
assert manifest['domain']==C.name
assert manifest['codeowners']==['@lukirenggli']
assert manifest['categories']==['energy.energy_prices']
assert manifest['config_flow'] and manifest['single_config_entry']
assert hacs['homeassistant']=='2026.11.0' and hacs['country']=='CH'
assert len([p for p in (ROOT/'custom_components').iterdir() if p.is_dir() and p.name!='__pycache__'])==1

def shape(value):
    return {k:shape(v) for k,v in value.items()} if isinstance(value,dict) else None
strings=json.loads((C/'strings.json').read_text())
for language in ('de','en'):
    assert shape(json.loads((C/f'translations/{language}.json').read_text()))==shape(strings)
for name,size in [('icon.png',256),('icon@2x.png',512)]:
    content=(C/'brand'/name).read_bytes()
    assert content[:8]==b'\x89PNG\r\n\x1a\n'
    assert struct.unpack('>II',content[16:24])==(size,size)
for required in ('README.md','LICENSE','PUBLISHING.md','TESTING.md','NOTICE.md','.github/workflows/validate.yml'):
    assert (ROOT/required).exists(),required
assert (ROOT/'assets/banner.png').exists()
readme=(ROOT/'README.md').read_text()
assert readme.count('<!-- ha-marketplace:exclude-start -->')==readme.count('<!-- ha-marketplace:exclude-end -->')
print('PASS: Python syntax, JSON, repository layout, metadata, translations and 256/512 px PNGs')
print('This is not a Hassfest or Marketplace-validator result.')
