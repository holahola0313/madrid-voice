"""Download only the two verified official Madrid files; reuse local copies."""
import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://data.insideairbnb.com/spain/comunidad-de-madrid/madrid/2026-09-17/data/'

def main():
    raw = ROOT / 'data/raw/2026-09-17'
    raw.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name in ['listings.csv.gz', 'reviews.csv.gz']:
        path = raw / name
        url = BASE + name
        if not path.exists():
            temp = path.with_suffix('.part')
            print('Downloading', url, flush=True)
            with urllib.request.urlopen(url, timeout=120) as response, temp.open('wb') as out:
                while block := response.read(1024 * 1024):
                    out.write(block)
            temp.replace(path)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.append(dict(file=name, url=url, snapshot='2026-09-17', bytes=path.stat().st_size,
                             sha256=digest, verified_at_utc=datetime.now(timezone.utc).isoformat()))
        print(name, path.stat().st_size, digest, flush=True)
    out = ROOT / 'outputs'
    out.mkdir(exist_ok=True)
    (out / 'download_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
