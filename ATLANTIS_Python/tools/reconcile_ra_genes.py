"""Reconcile updated SBML entities with CellDesigner source and HGNC symbols."""
import csv, json, re
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
base=Path(__file__).resolve().parents[2]/"research_sources"
qual=ET.parse(base/"ra243-source.sbml")
source=ET.parse(base/"ra243-source.interaction.sbml")
def attr(node,key):
    return next(v for k,v in node.attrib.items() if k.split('}')[-1]==key)
updated={attr(e,"qualitativeSpecies") for e in qual.findall(".//{*}output")}
symbols={}
aliases=defaultdict(set)
with (base/"hgnc_reference.tsv").open(encoding="utf8") as f:
    for row in csv.DictReader(f,delimiter="\t"):
        symbols[row["symbol"]]=row["hgnc_id"]
        for a in (row["prev_symbol"]+"|"+row["alias_symbol"]).split("|"):
            aliases[a].add(row["hgnc_id"])
entities={e.get("id"):e for e in source.findall(".//{*}species")}
refs={e.get("id"):e.get("name","") for t in ("protein","gene","RNA") for e in source.findall(".//{*}"+t)}
def resolve(s):
    if s in symbols:return {symbols[s]}
    return aliases[s] if s and len(aliases[s])==1 else set()
records=[]
for q in qual.findall(".//{*}qualitativeSpecies"):
    if attr(q,"id") not in updated:continue
    links=[v for e in q.iter() for v in e.attrib.values() if v.startswith("urn:casq:cdid:")]
    if len(links)!=1:raise ValueError(links)
    ent=entities[links[0].split(":")[-1]]
    ident=ent.find(".//{*}speciesIdentity")
    if ident is None:continue
    cls=ident.findtext("{*}class")
    if cls not in ("PROTEIN","GENE","RNA"):continue
    ref=next((x.text for x in ident if x.tag.endswith("Reference")),None)
    symbol=refs.get(ref,"")
    genes=resolve(symbol)
    if len(genes)==1:records.append([attr(q,"id"),attr(q,"name"),cls,symbol,next(iter(genes))])
(base/"ra243-source-gene-map.json").write_text(json.dumps(records,indent=1))
print("updated",len(updated),"resolved",len(records),"distinct",len({r[-1] for r in records}))
