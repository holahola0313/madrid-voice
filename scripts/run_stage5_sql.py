"""CLI for dashboard SQL09/10/11, with bound filter parameters."""
import argparse,sys
from pathlib import Path
from datetime import date
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from dashboard import data as d
from dashboard import experience as x
p=argparse.ArgumentParser();p.add_argument('query',choices=['coverage','topics','leads'])
p.add_argument('--district');p.add_argument('--room-type');p.add_argument('--start',default=d.START);p.add_argument('--end',default=d.END)
p.add_argument('--dimension',choices=['overall','district','room_type','month'],default='overall')
p.add_argument('--method',choices=['rule','ai'],default='rule');a=p.parse_args()
date.fromisoformat(a.start);date.fromisoformat(a.end)
if not d.START<=a.start<=a.end<=d.END:p.error('Dates must stay in the fixed analysis window.')
if a.query=='leads' and a.dimension!='overall':p.error('leads summarizes the selected scope; use topics for dimension comparisons.')
params=d.parameters(a.district,a.room_type,a.start,a.end,a.dimension,'关键词规则' if a.method=='rule' else '本地AI')
print({'coverage':d.coverage,'topics':d.topics,'leads':x.topic_counts}[a.query](params).to_csv(index=False))
