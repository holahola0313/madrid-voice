"""Read saved, privacy-reviewed real excerpts. No inference or evaluation."""
import json
from pathlib import Path

rows = json.loads((Path(__file__).parent / 'reviewed_cases.json').read_text(encoding='utf-8'))
for row in rows:
    print(row['case'], row['name'])
    print(row['excerpt'])
    for topic, labels in row['labels'].items():
        print(topic, ' | '.join(f'{method}: {label["mention_status"]}/{label["sentiment"]}' for method, label in labels.items()))
    print(row['translation_status'])
    print()
print('5 selected cases; saved whole-review labels, not predictions recomputed on excerpts.')
