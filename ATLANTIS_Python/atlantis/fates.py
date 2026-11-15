"""Cell-fate CSV expansion, wildcards, and original 0/1/2 activity matching."""
from dataclasses import dataclass
from itertools import product
import re
import numpy as np


@dataclass
class FateLogic:
    nodes: list[int]
    labels: list[str]
    patterns: np.ndarray
    headers: list[str]

    def associate(self, activities):
        a=np.asarray(activities)[self.nodes]
        hits=np.all(np.isnan(self.patterns)|(self.patterns==a),axis=1)
        return ' + '.join(sorted(set(name for name,hit in zip(self.labels,hits) if hit)))


def load_fate_logic(path, network):
    from .io import read_rows
    rows=read_rows(path)
    if len(rows)<2 or len(rows[0])<2: raise ValueError('Fate logic needs a header and at least one fate')
    headers=rows[0][1:]; nodes=[network.index(x) for x in headers]
    labels=[]; patterns=[]
    for row in rows[1:]:
        if not row[0].strip(): continue
        cells=(row[1:]+['']*len(nodes))[:len(nodes)]
        choices=[]
        for cell in cells:
            text=cell.strip().strip('[]')
            values=[float(x) for x in re.split(r'[\s;,]+',text) if x] if text else [np.nan]
            if any(not np.isnan(x) and x not in (0,1,2) for x in values):
                raise ValueError('Fate states must be 0, 1, 2 (oscillation), or blank (wildcard)')
            choices.append(values)
        for combination in product(*choices):
            labels.append(row[0].strip()); patterns.append(combination)
    if not labels: raise ValueError('No fate rules found')
    return FateLogic(nodes,labels,np.array(patterns),headers)
