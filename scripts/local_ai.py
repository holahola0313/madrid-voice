"""Offline ONNX sentence encoder + uncalibrated Spanish prototype classifier."""
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'.ai-packages'))
os.environ['HF_HUB_OFFLINE']='1'
os.environ['TOKENIZERS_PARALLELISM']='false'
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer
from topic_methods import aggregate,clauses,TOPICS

class LocalAI:
    def __init__(self,config):
        self.config=config
        self.directory=ROOT/'data/models/multilingual-minilm'
        self.manifest=json.loads((self.directory/'manifest.json').read_text())
        for entry in self.manifest['files']:
            if hashlib.sha256((self.directory/entry['name']).read_bytes()).hexdigest()!=entry['sha256']:
                raise ValueError('Model checksum mismatch')
        self.tokenizer=Tokenizer.from_file(str(self.directory/'tokenizer.json'))
        self.tokenizer.enable_padding(pad_id=0,pad_token='[PAD]')
        self.tokenizer.no_truncation()
        options=ort.SessionOptions();options.intra_op_num_threads=config['cpu_threads'];options.inter_op_num_threads=1
        options.log_severity_level=3
        self.session=ort.InferenceSession(str(self.directory/'onnx/model_quint8_avx2.onnx'),
                                         sess_options=options,providers=['CPUExecutionProvider'])
        self.prototypes=json.loads((ROOT/'config/ai_prototypes.json').read_text(encoding='utf-8'))
        texts=[];self.prototype_keys=[]
        for topic,classes in self.prototypes.items():
            for sentiment,examples in classes.items():
                for example in examples:texts.append(example);self.prototype_keys.append((topic,sentiment))
        self.prototype_vectors=self.encode(texts)

    def encode(self,texts):
        vectors=[];size=self.config['batch_size']
        for i in range(0,len(texts),size):
            batch=self.tokenizer.encode_batch(texts[i:i+size])
            if max(len(x.ids) for x in batch)>self.config['max_tokens']:
                raise ValueError('Token limit exceeded: split clause, never silently truncate.')
            values={'input_ids':np.array([e.ids for e in batch],dtype=np.int64),
                    'attention_mask':np.array([e.attention_mask for e in batch],dtype=np.int64),
                    'token_type_ids':np.array([e.type_ids for e in batch],dtype=np.int64)}
            feed={n.name:values[n.name] for n in self.session.get_inputs()}
            outputs=self.session.run(None,feed)
            emb=outputs[0]
            if emb.ndim==3:
                mask=values['attention_mask'][:,:,None]
                emb=(emb*mask).sum(axis=1)/np.maximum(mask.sum(axis=1),1)
            emb=emb/np.maximum(np.linalg.norm(emb,axis=1,keepdims=True),1e-12)
            vectors.append(emb.astype(np.float32))
            if len(texts)>100 and (i//size)%50==0:print(f'Encoded {min(i+size,len(texts))}/{len(texts)} clauses',flush=True)
        return np.concatenate(vectors) if vectors else np.empty((0,384),dtype=np.float32)

    def split(self,text):
        parts=clauses(text,self.config['max_clause_characters'])
        # Check actual subword length and halve rare long-token pieces recursively.
        self.tokenizer.no_padding()
        pending=parts[:];result=[]
        while pending:
            p=pending.pop(0)
            if len(self.tokenizer.encode(p['text']).ids)<=self.config['max_tokens']:
                result.append(p);continue
            mid=len(p['text'])//2
            at=p['text'].rfind(' ',0,mid)
            if at<=0:at=mid
            for a,b in reversed([(p['start'],p['start']+at),(p['start']+at,p['end'])]):
                if text[a:b].strip():pending.insert(0,dict(start=a,end=b,text=text[a:b]))
        self.tokenizer.enable_padding(pad_id=0,pad_token='[PAD]')
        return result

    def classify(self,text,parts,vectors):
        similarities=vectors@self.prototype_vectors.T
        labels=[]
        for topic in TOPICS:
            hits=[]
            groups={s:[i for i,key in enumerate(self.prototype_keys) if key==(topic,s)]
                    for s in ['positive','negative','neutral']}
            for row,p in zip(similarities,parts):
                scores={s:float(row[ix].max()) for s,ix in groups.items()}
                ranking=sorted(scores,key=scores.get,reverse=True)
                best=scores[ranking[0]];margin=best-scores[ranking[1]]
                if best<self.config['ai_uncertain_threshold']:continue
                mention='present' if best>=self.config['ai_present_threshold'] else 'uncertain'
                sentiment=ranking[0] if mention=='present' and margin>=self.config['ai_sentiment_margin'] else 'uncertain'
                hits.append({**p,'mention':mention,'sentiment':sentiment,'cosine_scores':scores,
                             'margin':margin,'best_similarity':best})
            labels.append(aggregate(text,topic,hits,'local_minilm_prototypes','all_similarity_below_uncertain_threshold'))
        return labels
