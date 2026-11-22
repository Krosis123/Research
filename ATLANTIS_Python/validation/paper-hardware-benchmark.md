# ATLANTIS biological node updates on IBM Quantum

16 November 2026

Five jobs ran on the physical IBM Quantum processor `ibm_fez`. Across the five circuits, 1,053 of 1,280 shots (82.3%) reproduced the expected pair of Boolean outputs. The expected pair was the most frequent outcome in every job.

| Paper case | Source network | Nodes in source model | Node tested | Correct shots | Accuracy | IBM job ID |
|---|---|---:|---|---:|---:|---|
| 1 | Budding yeast cell cycle | 11 | MBF | 207/256 | 80.9% | `dbtifd3nlcms73ajb7og` |
| 2 | MCF-7 p53, control | 16 | ATM | 192/256 | 75.0% | `dbtifdrsbsbs73cb3f6g` |
| 2 | MCF-7 p53, etoposide | 16 | ATM | 175/256 | 68.4% | `dbtifesvruos73ccee1g` |
| 3 | Colorectal tumorigenesis | 201 | Actin | 241/256 | 94.1% | `dbtiffkvruos73ccee30` |
| 4 | HCT-116 colorectal cancer | 201 | Actin | 238/256 | 93.0% | `dbtifgjsbsbs73cb3fag` |

Network size counts the Boolean variables in each model. Some represent groups of genes (such as Cln1-2 in yeast), external signals (DNA_damage), or outcomes (Apoptosis). The model files provide node counts. A count of distinct genes would require mapping these variables to gene identifiers.

## What each shot measured

For each model, the runner selected the first nonlinear node rule with two to four inputs that produced both output values in the local test states. It prepared two copies of that rule in one circuit. The first received an input for which classical ATLANTIS predicted 0, and the second received an input for which it predicted 1. IBM reports the second measurement bit first, so the expected register was `10`. Accuracy is the fraction of raw shots returning exactly `10`.

## Interpretation

Agreement ranged from 68.4% for ATM in the etoposide model to 94.1% for Actin in case 3. Each percentage describes one circuit, two chosen inputs, and one hardware run. The design does not establish whether differences arose from circuit structure, device noise, or run-to-run variation. The 201-node entries describe the source models. Their hardware circuits evaluated the selected Actin rule only.

In a separate local check, the compiled and classical one-step updates agreed for all 2,048 yeast states, all 65,536 states of each MCF-7 model, and 128 sampled states per 201-node model. Attractor discovery was also performed locally.

[Raw IBM measurement counts](paper-hardware.json) · [Benchmark runner](../tools/check_paper_transitions.py) · [ATLANTIS paper](https://doi.org/10.1038/s41598-018-22031-3)

## Gene count for the two colorectal models

The 201-node models share 184 identical Boolean update tables. Counting each distinct rule target once gives 184. A conservative manual mapping of individual target labels to human gene symbols gives 85 distinct genes per model. This is a lower bound under the assignments in the [node-by-node audit](colorectal-rule-gene-audit.tsv). Grouped labels, unassigned aliases and protein states are left unresolved. Chemical species and logic variables contribute no gene. The other 17 nodes comprise 13 external inputs and four phenotypes. The [original model and supplementary rule tables](https://pmc.ncbi.nlm.nih.gov/articles/PMC5072344/) describe the signaling components.
