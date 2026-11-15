"""Compare published CRC series against archived replicates without selecting a fit."""
import csv
import json
from pathlib import Path
from statistics import mean


def main():
    root=Path('validation')
    rows=json.loads((root/'colorectal-three-replicates.json').read_text())
    published={'Control':.79,'APC':.79,'APC+RAS':.39,'APC+RAS+PTEN':.41,'APC+RAS+PTEN+P53':.013}
    result=[]
    for condition, value in published.items():
        group=sorted((row for row in rows if row['condition']==condition),key=lambda row:row['replicate'])
        assert len(group)==3
        counts=[row['combined_fate_counts'].get('Normal Proliferation',0) for row in group]
        resolved=[row['rows']-row['combined_fate_counts'].get('unresolved',0) for row in group]
        fractions=[c/n for c,n in zip(counts,resolved)]
        avg=mean(fractions)
        pooled=sum(counts)/sum(resolved)
        result.append(dict(condition=condition,published=value,simulation_1=fractions[0],
                           simulation_2=fractions[1],simulation_3=fractions[2],
                           paper_described_mean=avg,pooled_resolved_sensitivity=pooled,
                           pooled_all_starts_sensitivity=sum(counts)/sum(x['rows'] for x in group),
                           mean_minus_published=avg-value,resolved_total=sum(resolved)))
    with (root/'colorectal-aggregation-024.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(result[0]))
        writer.writeheader()
        writer.writerows(result)


if __name__ == '__main__':
    main()
