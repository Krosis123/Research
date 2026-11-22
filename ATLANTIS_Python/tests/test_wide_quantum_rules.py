"""Regression cases for wide biological networks in the quantum adapter."""
import numpy as np

from atlantis.model import Network, TruthRule
from atlantis.quantum.adapter import QuantumNetwork


def test_msb_source_order_above_synthesis_fanin():
    # A supplied table does not require synthesizing 2**fanin network states.
    names = [f'n{i}' for i in range(14)]
    addr = np.arange(1 << 13)
    outputs = ((addr >> 12) ^ (addr >> 1)) & 1
    net = Network(names, rules=[None]*13+[TruthRule(list(range(13)), outputs)])
    q = QuantumNetwork(net)
    for state in (1 << 13, 1 << 2, (1 << 13) | (1 << 2), 1 << 1):
        assert q.step(state) & 1 == outputs[state >> 1]


def test_weighted_source_index_preserves_bits_above_64():
    weights = np.zeros((70, 70))
    weights[0, -1] = 1
    net = Network(list(map(str, range(70))), weights=weights)
    q = QuantumNetwork(net)
    assert q.step(1 << 69) == (1 << 69) | 1
