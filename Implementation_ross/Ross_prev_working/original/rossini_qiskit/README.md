# Rossini Boolean-network attractor search — modern Qiskit reproduction

This project is a clean reimplementation of the 4-gene demonstration from:

Mirko Rossini, Felix M. Weidner, Joachim Ankerhold, Hans A. Kestler,
"A novel quantum algorithm for efficient attractor search in gene regulatory networks."

The goal is to reproduce the paper first, then modify the suppression stage
with an ancilla-subspace construction.

## 1. Environment setup on Windows PowerShell

Create a fresh folder:

```powershell
mkdir C:\quantum_rosini
cd C:\quantum_rosini
```

Copy the files from this project into that folder.

Create a virtual environment:

```powershell
python -m venv .venv
```

If PowerShell blocks activation for this window:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
```

Activate:

```powershell
.\.venv\Scripts\Activate.ps1
```

Upgrade pip:

```powershell
python -m pip install --upgrade pip
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Verify:

```powershell
python -c "import qiskit, qiskit_aer; print('Qiskit', qiskit.__version__); print('Aer', qiskit_aer.__version__)"
```

## 2. First run: classical network only

```powershell
python network.py
```

The Boolean rules are:

- A' = A AND D
- B' = A AND B
- C' = C AND D
- D' = B OR C

The attractors should be:

- 0000, basin size 11
- 0011, basin size 2
- 1011, basin size 1
- 1101, basin size 1
- 1111, basin size 1

## 3. Verify the deletion mathematics with NumPy

```powershell
python numpy_reference.py
```

Expected surviving initial-state probabilities:

After deleting basin 0000 (11 of 16 states):

- 0011, 0111, 1011, 1101, 1111 each have probability 0.2.

After additionally deleting basin 1011:

- 0011, 0111, 1101, 1111 each have probability 0.25.

After additionally deleting basin 0011:

- 1101, 1111 each have probability 0.5.

After additionally deleting basin 1111:

- 1101 has probability 1.

This is an important checkpoint: it verifies the Liu-Ouyang/Rossini phase
angles independently of Qiskit.

## 4. Run the full Rossini Qiskit experiment

```powershell
python experiment_rossini.py
```

The script:

1. prepares a uniform superposition over the 16 initial gene states;
2. applies the reversible Boolean-network evolution T;
3. phase-marks attractors whose basins should be removed;
4. applies T-dagger so that the phase is inherited by the entire basin;
5. applies the matched Hadamard / |0000>-phase / Hadamard operation;
6. repeats this J times when required;
7. evolves forward again;
8. measures the surviving attractor.

Suppression order:

```text
0000 -> 1011 -> 0011 -> 1111
```

leaving:

```text
1101
```

with probability approaching 1 in the noiseless simulator.

## 5. Quantum-counting stage

The paper's Step 1.1 obtains M, the total number of states in already-known
basins, using quantum counting.

The baseline reproduction above supplies the exact M values so that it is easy
to debug the suppression circuit independently.

To test the counting stage:

```powershell
python experiment_counting.py
```

This uses phase estimation on a Grover iterate whose oracle is:

```text
T
-> phase known attractors by pi
-> T-dagger
```

so it phase-marks the complete basins without listing their states explicitly.

This circuit is much more expensive to simulate than the suppression-only
experiment because controlled powers of the Grover operator are required.

## File map

- `network.py` — classical Boolean network and basin sanity checks
- `quantum_network.py` — reversible T operator
- `phase_tools.py` — conditional basis-state phase shifts
- `rossini.py` — exact Rossini/Liu-Ouyang suppression
- `experiment_rossini.py` — full 4-gene reproduction
- `counting.py` — quantum-counting implementation for M
- `experiment_counting.py` — test counting on successive known basins
- `numpy_reference.py` — independent math verification

## Next modification

Do not modify `rossini.py` yet.

Once `experiment_rossini.py` reproduces the expected results locally, create a
separate ancilla implementation. That gives us a clean A/B comparison:

```text
Rossini baseline
vs.
ancilla-subspace version
```

without contaminating the reference implementation.
