# ATLANTIS 0.2.4 random network starter pack

The Boolean examples have a two-node reversible core and randomly generated
downstream rules. This construction gives a known terminal horizon of T=1.
The weighted examples have three randomly selected incoming edges per target
and random basal values. Seeds are 24006 and 24008.

## Open the examples

Right-click the main window and choose **Open Python Network**. Select one of
the Boolean JSON or weighted CSV files. For deterministic or probabilistic
analysis, use **Generate States** or load the matching all-bit-states CSV via
**Custom States**. The six-node state list has 64 rows and the eight-node one
has 256 rows. Probabilistic analysis uses the weighted examples.

For a first quantum run, use a Boolean example, T=1, engine aer_mps,
counting exact, and stop policy classical_audit. Exact counting and the
coverage certificate use classical enumeration. For a separate genuine QPE
experiment, select qpe_aer and stop policy qpe. Start with 4 precision bits
for six nodes or 5 for eight nodes if your resource budget allows. The
logical widths at these settings are 16 and 21 qubits, respectively.
QPE adds circuit depth and may be inconclusive. These QPE runs were not timed.

## Exact input formats

### Boolean expression JSON (UTF-8)

```json
{
  "name": "Two-node example",
  "rules": {
    "G1": "~G2",
    "G2": "G1 & G2"
  }
}
```

The keys of rules are the node names, in bit order. Give every node one rule.
Operators in this example format are ~ (NOT), & (AND), | (OR), ^ (XOR),
parentheses, and constants 0 or 1. Updates are synchronous.

### Weighted network CSV

```csv
,G1,G2
G1,0,1
G2,-1,0
basal,0,0
```

The header lists target columns. The next N rows list sources in the same
order as the header. Weight W[i,j] is the effect of source i on target j.
The final row contains one basal value per target. A positive summed input
sets the target to 1, a negative one sets it to 0, and a zero sum retains
its previous state in deterministic analysis.

### Truth-table folder

Use **Generate Network** and select rules-based input. Select the supplied
Node List.txt and its Boolean logic for nodes folder. The node list has one
node name per line. Each target has one file named exactly Target.txt.
The first row lists source columns in order and the target as the final
column. Supply all 2^k source assignments in ascending binary order,
with the first source as the most significant bit. This example, G3.txt,
makes G3 the XOR of G1 and G2:

```csv
G1,G2,G3
0,0,0
0,1,1
1,0,1
1,1,0
```

### Initial-state CSV

One row per state, comma-separated, with exactly N entries of 0 or 1
in network node order. No header and no state-index column.

## Checks

The JSON and truth-table versions produce identical transitions on every
input. Both Boolean networks were verified by exhaustive deterministic
analysis and a 256-shot unsuppressed Aer MPS forward run at T=1. The six-node
case has two fixed points and one two-cycle. The eight-node case has two
two-cycles. Both weighted cases ran deterministic and pruned probabilistic
analysis. Their 200-step probabilistic runs reached the step limit, so those
outputs are finite-iteration estimates. See verification.json for details.
