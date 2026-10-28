"""Run a saved read-only SQL query with optional cohort filters."""
import argparse
import csv
import io
import sqlite3
import sys
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
def main():
    p=argparse.ArgumentParser()
    p.add_argument('sql_file',help='Filename under sql/, e.g. 06_filtered_coverage.sql')
    p.add_argument('--district')
    p.add_argument('--room-type')
    p.add_argument('--start-date',default='2025-09-01')
    p.add_argument('--end-date',default='2026-08-31')
    args=p.parse_args()
    path=(ROOT/'sql'/args.sql_file).resolve()
    if path.parent!=(ROOT/'sql').resolve() or path.name=='00_schema.sql':
        p.error('Choose an analysis SQL file directly under sql/.')
    if path.name not in ('06_filtered_coverage.sql','08_future_topic_metrics.sql') and (
        args.district is not None or args.room_type is not None or
        args.start_date!='2025-09-01' or args.end_date!='2026-08-31'):
        p.error('Filters are supported by queries 06 and 08 only; other queries cover the fixed cohort.')
    date.fromisoformat(args.start_date);date.fromisoformat(args.end_date)
    if not '2025-09-01'<=args.start_date<=args.end_date<='2026-08-31':
        p.error('Filter must be within the fixed analysis window.')
    db=ROOT/'data/processed/madrid_voice.sqlite'
    conn=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    conn.execute('PRAGMA query_only=ON')
    cur=conn.execute(path.read_text(encoding='utf-8'),dict(district=args.district,room_type=args.room_type,
                    start_date=args.start_date,end_date=args.end_date))
    output=io.StringIO(newline='')
    writer=csv.writer(output,lineterminator='\n');writer.writerow([c[0] for c in cur.description]);writer.writerows(cur)
    sys.stdout.write(output.getvalue())
    conn.close()
if __name__=='__main__':
    main()
