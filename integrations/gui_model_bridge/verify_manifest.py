"""Verify frozen portable bytes; never imports a host or calls a model."""
from pathlib import Path
import hashlib,json
root=Path(__file__).resolve().parent
manifest=json.loads((root/'source-manifest.json').read_bytes())
for name,expected in manifest['files'].items():
 if Path(name).name!=name:raise SystemExit('Unsafe manifest filename')
 actual=hashlib.sha256((root/name).read_bytes()).hexdigest()
 if actual!=expected:raise SystemExit('Source manifest mismatch: '+name)
print(json.dumps(dict(status='SOURCE_BYTES_MATCH',files=len(manifest['files']),scope=manifest['scope'])))
