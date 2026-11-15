"""Exact state generation, with the original optional sampling and initial-node fixing."""
import numpy as np
from .model import boolean_states, decimal_to_binary


def all_states(n, max_bytes=512*1024**2):
    if n < 1: raise ValueError('At least one node is required')
    count = 2**n
    if count*n > max_bytes:
        raise MemoryError(f'Full enumeration needs {count*n:,} bytes. Select random or custom states explicitly.')
    ids = np.arange(count,dtype=np.uint64)
    return ((ids[:,None] >> np.arange(n-1,-1,-1,dtype=np.uint64)) & 1).astype(np.uint8)


def random_states(n, count, seed=None):
    if n < 1 or count < 1 or count > 2**n: raise ValueError('Sample size must be between 1 and 2^N')
    if count*n > 512*1024**2: raise MemoryError('Requested sample exceeds 512 MiB')
    rng = np.random.default_rng(seed)
    # Original method: independent fair bits, removing duplicates in first-occurrence order.
    result=[]; seen=set()
    while len(result) < count:
        rows=rng.integers(0,2,(count-len(result),n),dtype=np.uint8)
        for row in rows:
            key=row.tobytes()
            if key not in seen: seen.add(key); result.append(row)
    return np.array(result,dtype=np.uint8)


def fix_initial_nodes(network, states, assignments):
    s=boolean_states(states,network.n).copy()
    for name,value in assignments.items():
        if value not in (0,1): raise ValueError('Fixed node values must be Boolean')
        s[:,network.index(name)]=value
    return s
