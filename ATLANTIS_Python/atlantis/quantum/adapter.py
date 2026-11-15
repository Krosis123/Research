"""Translate canonical ATLANTIS models to reversible ANF without changing dynamics."""
import numpy as np
from ..model import decimal_to_binary
from ..expressions import ExpressionRule
from .ross.model import Rule


class QuantumNetwork:
    def __init__(self, network, max_fanin=12, max_terms=4096):
        network.require_resolved_rules()
        self.network = network.copy()
        self.name = network.name
        self.genes = tuple(network.names)
        self.n = network.n
        self.size = 1 << self.n
        self.rules = []
        for target in range(self.n):
            r = network.rules[target] if network.weights is None else None
            if isinstance(r, ExpressionRule):
                inputs = tuple(r.sources)
                terms = r.anf(max_terms=max_terms)
            else:
                if network.weights is not None:
                    inputs = tuple(sorted(set(np.flatnonzero(network.weights[:,target])) | {target}))
                else: inputs = tuple(r.sources) if r else (target,)
                if len(inputs)>max_fanin:
                    raise ValueError(f'Node {network.names[target]} requires {len(inputs)} inputs; bounded table compiler limit is {max_fanin}. Use a symbolic rule where possible.')
                # Local input bit j is ANF mask bit j, whereas ATLANTIS tables are MSB first.
                states=np.zeros((1 << len(inputs),self.n),dtype=np.uint8)
                for j,source in enumerate(inputs): states[:,source]=(np.arange(len(states)) >> j) & 1
                values=network.step(states)[:,target].copy()
                for j in range(len(inputs)):
                    for mask in range(len(values)):
                        if mask & (1<<j): values[mask] ^= values[mask ^ (1<<j)]
                terms=tuple(int(x) for x in np.flatnonzero(values))
                if len(terms)>max_terms: raise ValueError('ANF term budget exceeded')
            # Substitute hard clamps into symbolic ANF (truth-derived ANF is already equivalent).
            simplified=set()
            for term in terms:
                reduced=term;zero=False
                for j,source in enumerate(inputs):
                    name=network.names[source]
                    if term&(1<<j) and name in network.clamped:
                        if not network.clamped[name]:zero=True;break
                        reduced &= ~(1<<j)
                if not zero:
                    if reduced in simplified:simplified.remove(reduced)
                    else:simplified.add(reduced)
            if network.names[target] in network.clamped:
                simplified={0} if network.clamped[network.names[target]] else set()
            self.rules.append(Rule('',inputs,(),tuple(sorted(simplified))))

    def step(self,x):
        out=0
        for rule in self.rules:
            mask=sum(((x >> (self.n-1-source)) & 1)<<j for j,source in enumerate(rule.inputs))
            value=sum((mask & term)==term for term in rule.anf_terms) & 1
            out=(out<<1)|value
        return out

    def as_bits(self,x): return format(x,f'0{self.n}b')
