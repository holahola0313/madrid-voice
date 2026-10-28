"""Download public weights only. No review data are accessed or transmitted."""
import hashlib
import json
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPO='sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
REVISION='e8f8c211226b894fcb81acc59f3b34ba3efd5f42'
DEST=ROOT/'data/models/multilingual-minilm'
FILES=['onnx/model_quint8_avx2.onnx','tokenizer.json','tokenizer_config.json','config.json','1_Pooling/config.json','README.md']

def main():
    DEST.mkdir(parents=True,exist_ok=True)
    manifest_path=DEST/'manifest.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_text())
        for entry in manifest['files']:
            if hashlib.sha256((DEST/entry['name']).read_bytes()).hexdigest()!=entry['sha256']:
                raise ValueError('Cached model file changed')
        print('Verified cached model; no download.');return
    revision=REVISION
    manifest={'repo':REPO,'revision':revision,'license':'apache-2.0','files':[]}
    for name in FILES:
        path=DEST/name;path.parent.mkdir(parents=True,exist_ok=True)
        url=f'https://huggingface.co/{REPO}/resolve/{revision}/{name}'
        print('Downloading',name,flush=True)
        tmp=path.with_suffix(path.suffix+'.part')
        with urllib.request.urlopen(url,timeout=120) as r,tmp.open('wb') as f:
            while block:=r.read(1024*1024): f.write(block)
        tmp.replace(path)
        manifest['files'].append({'name':name,'url':url,'bytes':path.stat().st_size,
                                  'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest_path.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
