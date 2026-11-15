"""NetworkDataStructure and synchronous state updates (source/target orientation)."""
from dataclasses import dataclass, field
from copy import deepcopy
import numpy as np
from .expressions import ExpressionRule


def boolean_states(values, n=None):
    a = np.asarray(values)
    if a.ndim == 1:
        a = a.reshape(1, -1)
    if a.ndim != 2 or (n is not None and a.shape[1] != n):
        raise ValueError(f'States must have {n if n is not None else "N"} columns')
    if not np.all((a == 0) | (a == 1)):
        raise ValueError('States must contain only 0 and 1')
    return a.astype(np.uint8)


def binary_to_decimal(states):
    a = np.asarray(states, dtype=np.uint8)
    if a.shape[-1] <= 62:
        return a @ (1 << np.arange(a.shape[-1]-1, -1, -1, dtype=np.int64))
    return np.array([sum(int(v) << (len(row)-1-i) for i,v in enumerate(row))
                     for row in np.atleast_2d(a)], dtype=object)


def decimal_to_binary(values, n):
    vals = np.atleast_1d(values)
    if n < 1 or any(int(v) < 0 or int(v) >= 2**n or int(v) != v for v in vals):
        raise ValueError('Decimal state is outside the network state space')
    return np.array([[(int(v) >> j) & 1 for j in range(n-1,-1,-1)] for v in vals], dtype=np.uint8)


@dataclass
class TruthRule:
    sources: list[int]
    outputs: np.ndarray

    def __post_init__(self):
        if any(type(i) is not int or i<0 for i in self.sources) or len(set(self.sources))!=len(self.sources):
            raise ValueError('Truth-rule sources must be distinct nonnegative integer indices')
        if len(self.sources)>20: raise ValueError('Truth table exceeds 20-input import budget; use symbolic expressions')
        a = np.asarray(self.outputs).reshape(-1)
        if a.size != 2**len(self.sources) or not np.all((a == 0) | (a == 1)):
            raise ValueError('Truth rule requires one Boolean output for every binary input')
        self.outputs = a.astype(np.uint8)


@dataclass
class Network:
    names: list[str]
    weights: np.ndarray | None = None
    basal: np.ndarray | None = None
    rules: list[TruthRule | None] | None = None
    name: str = 'Network'
    positions: dict = field(default_factory=dict)
    clamped: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        self.names = [str(x).strip() for x in self.names]
        if not self.names or any(not x for x in self.names) or len(set(x.casefold() for x in self.names)) != self.n:
            raise ValueError('Node names must be nonempty and unique (case insensitive)')
        if self.weights is not None:
            self.weights = np.asarray(self.weights, dtype=float)
            self.basal = np.zeros(self.n) if self.basal is None else np.asarray(self.basal,dtype=float).reshape(-1)
            if self.weights.shape != (self.n,self.n) or self.basal.shape != (self.n,):
                raise ValueError('Interaction weights must be N x N and basal values length N')
            if not np.isfinite(self.weights).all() or not np.isfinite(self.basal).all():
                raise ValueError('Weights and basal values must be finite')
        elif self.rules is None or len(self.rules) != self.n:
            raise ValueError('Provide weights or one truth rule per node')
        if self.rules is not None:
            for rule in self.rules:
                if rule and any(i < 0 or i >= self.n for i in rule.sources):
                    raise ValueError('Truth rule source is outside node list')
        if any(name not in self.names or type(value) not in (int,bool) or value not in (0,1) for name,value in self.clamped.items()):
            raise ValueError('Clamps must map exact node names to 0 or 1')
        for key in ('external_inputs', 'unspecified_rules', 'assumed_identity_rules'):
            names = self.metadata.get(key, [])
            if not isinstance(names, list) or any(name not in self.names for name in names):
                raise ValueError(f'{key} must be a list of exact node names')
        if any(self.weights is not None or self.rules[self.names.index(name)] is not None
               for name in self.metadata.get('external_inputs', [])):
            raise ValueError('External inputs must be rule-based nodes without update tables')

    @property
    def n(self): return len(self.names)

    @property
    def kind(self): return 'WeightsBased' if self.weights is not None else 'RulesBased'

    @property
    def adjacency(self):
        if self.weights is not None: return self.weights.copy()
        a = np.zeros((self.n,self.n))
        for j,r in enumerate(self.rules):
            if r: a[r.sources,j] = 1
        return a

    def index(self, name):
        try: return [x.casefold() for x in self.names].index(name.strip().casefold())
        except ValueError: raise ValueError(f'Unknown node: {name}') from None

    def step(self, states):
        self.require_resolved_rules()
        s = boolean_states(states, self.n)
        for name,value in self.clamped.items():s[:,self.names.index(name)]=value
        result = s.copy()
        if self.weights is not None:
            total = s @ self.weights + self.basal
            result[total > 0] = 1
            result[total < 0] = 0
        else:
            for j, r in enumerate(self.rules):
                if r is not None:
                    result[:,j] = r.evaluate(s) if isinstance(r,ExpressionRule) else r.outputs[binary_to_decimal(s[:,r.sources]).astype(np.intp)]
        for name,value in self.clamped.items():result[:,self.names.index(name)]=value
        return result

    def require_resolved_rules(self):
        """Reject incomplete imported dynamics unless explicitly resolved."""
        if self.rules is None:
            return
        external = self.metadata.get('external_inputs', [])
        unresolved = [name for name in self.metadata.get('unspecified_rules', [])
                      if name not in self.clamped and name not in external
                      and self.rules[self.names.index(name)] is None]
        if unresolved:
            raise ValueError('Unspecified update rules: ' + ', '.join(unresolved))

    def copy(self): return deepcopy(self)

    def mutate(self, entries):
        """Source semantics: +/-1000 basal; link deletion fixes rule input to zero."""
        new = self.copy()
        for name,value in entries:
            if value not in (0,1,2): raise ValueError('Mutation value must be 0, 1, or 2 (link deletion)')
            if value == 2:
                pair = name.split('>')
                if len(pair) != 2: raise ValueError('Link mutations use Source>Target,2')
                source,target = (new.index(x) for x in pair)
                if not new.adjacency[source,target]: raise ValueError(f'Link does not exist: {name}')
                if new.weights is not None: new.weights[source,target] = 0
                else:
                    r = new.rules[target]
                    if isinstance(r,ExpressionRule):
                        import ast
                        tree=deepcopy(r.tree)
                        class RemoveInput(ast.NodeTransformer):
                            def visit_Name(self,node):
                                return ast.Constant(0) if node.id==f'_node_{source}' else node
                        tree=RemoveInput().visit(tree)
                        expr=ast.unparse(tree)
                        new.rules[target]=ExpressionRule(expr,new.names)
                        continue
                    k = r.sources.index(source)
                    inputs = decimal_to_binary(range(len(r.outputs)),len(r.sources))
                    outputs = r.outputs[inputs[:,k] == 0]
                    sources = r.sources.copy(); sources.pop(k)
                    new.rules[target] = TruthRule(sources,outputs)
            else:
                j = new.index(name)
                if new.weights is not None: new.basal[j] = 1000 if value else -1000
                elif new.names[j] in new.metadata.get('external_inputs', []):
                    new.clamped[new.names[j]] = value
                else:
                    new.rules[j] = TruthRule([], [value])
        return new
