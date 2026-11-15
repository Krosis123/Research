"""Benchmark utility from Supplementary Data: full DNF export, without minimization."""
from pathlib import Path
from .io import read_rows


def truth_tables_to_boolnet(folder,output):
    lines=['targets,factors']
    for path in sorted(Path(folder).glob('*.txt')):
        rows=read_rows(path); sources=[s.lower() for s in rows[0][:-1]]; target=rows[0][-1].lower(); terms=[]
        for row in rows[1:]:
            if int(row[-1])==1:
                terms.append('('+' & '.join(('!'+name if int(value)==0 else name) for name,value in zip(sources,row[:-1]))+')')
        lines.append(target+', '+(' | '.join(terms) if terms else '0'))
    Path(output).write_text('\n'.join(lines)+'\n',encoding='utf-8')
