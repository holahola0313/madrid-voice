"""Explainable Spanish rules and shared, offset-preserving clause utilities."""
import json
import re
import unicodedata
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RULES=json.loads((ROOT/'config/spanish_rules.json').read_text(encoding='utf-8'))
TOPICS=list(RULES)
REGEX={t:{k:re.compile(v) for k,v in spec.items()} for t,spec in RULES.items()}

def fold(text):
    return ''.join(c for c in unicodedata.normalize('NFD',text.lower()) if not unicodedata.combining(c))

def clauses(text,max_chars=240):
    """Split punctuation/adversatives, then short word-aligned chunks; exact offsets."""
    boundaries=list(re.finditer(r'[.!?;\n]+|\b(?:pero|aunque|sin embargo)\b',text,flags=re.I))
    ranges=[];start=0
    for m in boundaries:
        ranges.append((start,m.start()));start=m.end()
    ranges.append((start,len(text)))
    out=[]
    for a,b in ranges:
        while a<b:
            while a<b and text[a].isspace():a+=1
            if a==b:break
            end=min(a+max_chars,b)
            if end<b:
                space=text.rfind(' ',a,end)
                if space>a:end=space
            end_trim=end
            while end_trim>a and text[end_trim-1].isspace():end_trim-=1
            if end_trim>a:out.append({'start':a,'end':end_trim,'text':text[a:end_trim]})
            a=end
    return out

def aggregate(text,topic,hits,method,absent_reason='no_topic_cue'):
    if not hits:
        return dict(topic=topic,mention_status='absent',sentiment='not_applicable',evidence_text='',spans=[],reason=absent_reason)
    certain=[h for h in hits if h.get('mention','present')=='present']
    vals={h['sentiment'] for h in certain}
    if not certain:mention,sentiment='uncertain','uncertain'
    else:
        mention='present'
        if 'negative' in vals and 'positive' in vals:sentiment='mixed'
        elif 'negative' in vals:sentiment='negative'
        elif 'positive' in vals:sentiment='positive'
        elif 'uncertain' in vals:sentiment='uncertain'
        else:sentiment='neutral'
    a=min(h['start'] for h in hits);b=max(h['end'] for h in hits)
    return dict(topic=topic,mention_status=mention,sentiment=sentiment,
                evidence_text=text[a:b],spans=hits,reason=method+'; positive+negative=mixed; evidence spans are retrieval, not proof of correctness')

def rule_predict(text):
    results=[]
    for topic,rx in REGEX.items():
        hits=[]
        for part in clauses(text):
            s=fold(part['text'])
            mentions=list(rx['mention'].finditer(s))
            if not mentions:continue
            signs=[];cues=[]
            for valence in ['positive','negative']:
                for m in rx[valence].finditer(s):
                    # Restrict generic sentiment to vicinity of topic mention.
                    if min(abs(m.start()-q.start()) for q in mentions)>60:continue
                    prefix=s[max(0,m.start()-45):m.start()]
                    tail=re.findall(r'\b\w+\b',prefix)[-4:]
                    negated=any(w in ('no','nunca','sin','tampoco') for w in tail)
                    if re.search(r'no (solo|solamente)\b',prefix):negated=False
                    # Cues such as 'no funciona' already express their polarity.
                    cue=m.group()
                    if cue.startswith(('no ','sin ')):negated=False
                    value=('negative' if valence=='positive' else 'positive') if negated else valence
                    signs.append(value);cues.append({'cue':cue,'base':valence,'negated':negated,'result':value})
            if re.search(r'\b(quiza|quizas|tal vez|no se si|podria|no es que)\b',s):
                sentiment='uncertain'
            elif 'positive' in signs and 'negative' in signs:sentiment='mixed'
            elif signs:sentiment=signs[0]
            elif re.search(r'\b(hay|tiene|dispone|se realiza|se recogen)\b',s):sentiment='neutral'
            else:sentiment='uncertain'
            hits.append({**part,'sentiment':sentiment,'mention':'present','cues':cues,
                         'topic_cues':[m.group() for m in mentions]})
        # Mixed within a clause must also survive aggregation.
        label=aggregate(text,topic,hits,'spanish_rules')
        if any(h['sentiment']=='mixed' for h in hits):label['sentiment']='mixed'
        results.append(label)
    return results
