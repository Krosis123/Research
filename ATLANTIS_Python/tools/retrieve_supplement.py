"""Retrieve only supplement links actually advertised by the paper's PMC page."""
from pathlib import Path
from urllib.parse import urljoin
import re,requests
url='https://pmc.ncbi.nlm.nih.gov/articles/PMC12485557/'
r=requests.get(url,timeout=30)
links=re.findall(r'href=["\x27]([^"\x27]+)',r.text)
links=[urljoin(url,l) for l in links if 'mmc' in l or ('supp' in l and '.pdf' in l)]
print('Discovered supplement links:',links)
for i,link in enumerate(links):
    response=requests.get(link,timeout=30)
    if response.content.startswith(b'%PDF'):
        Path(f'../research_sources/rossini-supplement-{i}.pdf').write_bytes(response.content)
        print('Saved PDF',i)
