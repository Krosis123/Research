"""Safe vector Boolean expressions and bounded symbolic ANF synthesis.

Quote arbitrary node identifiers with backticks. No eval/exec is used.
ANF is a polynomial over GF(2); monomials are sets of input indices.
"""
import ast
import re
from functools import reduce
import numpy as np


class ExpressionRule:
    def __init__(self, expression, names):
        if not isinstance(expression, str) or len(expression) > 16384:
            raise ValueError('Expression must be text of at most 16384 characters')
        self.expression = expression
        self.names = list(names)
        aliases = {f'_node_{i}': i for i in range(len(names))}
        def quoted(match):
            try: return f'_node_{names.index(match[1])}'
            except ValueError: raise ValueError('Unknown quoted node') from None
        text = re.sub(r'`([^`]+)`', quoted, expression)
        names_to_index = {n: i for i, n in enumerate(names) if n.isidentifier()}
        # Rewrite identifiers before operators so a quoted keyword remains a node.
        def token(match):
            value = match[0]
            if value in aliases: return value
            if value in names_to_index: return f'_node_{names_to_index[value]}'
            return {'AND':'&','OR':'|','XOR':'^','NOT':'~',
                    'and':'&','or':'|','xor':'^','not':'~'}.get(value, value)
        text = re.sub(r'\b[A-Za-z_]\w*\b', token, text).replace('!', '~').strip()
        try: self.tree = ast.parse(text, mode='eval').body
        except (SyntaxError, RecursionError): raise ValueError('Invalid Boolean expression') from None
        nodes = list(ast.walk(self.tree))
        if len(nodes) > 2048: raise ValueError('Expression exceeds AST budget')
        sources = set()
        def validate(node, depth=0):
            if depth > 100: raise ValueError('Expression nesting exceeds budget')
            if isinstance(node, ast.Name) and node.id in aliases:
                sources.add(aliases[node.id])
            elif isinstance(node, ast.Constant) and type(node.value) in (int, bool) and node.value in (0, 1): pass
            elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Invert): validate(node.operand, depth+1)
            elif isinstance(node, ast.BinOp) and type(node.op) in (ast.BitAnd, ast.BitOr, ast.BitXor):
                validate(node.left, depth+1); validate(node.right, depth+1)
            else: raise ValueError('Unsupported Boolean syntax: '+type(node).__name__)
        validate(self.tree)
        self.sources = sorted(sources)

    def evaluate(self, states):
        def run(node):
            if isinstance(node, ast.Name): return states[:, int(node.id[6:])]
            if isinstance(node, ast.Constant): return int(node.value)
            if isinstance(node, ast.UnaryOp): return 1 ^ run(node.operand)
            a,b = run(node.left), run(node.right)
            if isinstance(node.op, ast.BitAnd): return a & b
            if isinstance(node.op, ast.BitOr): return a | b
            return a ^ b
        return run(self.tree)

    def anf(self, max_terms=4096, max_products=100000):
        products = 0
        def multiply(a,b):
            nonlocal products
            products += len(a)*len(b)
            if products > max_products: raise ValueError('Symbolic ANF product budget exceeded')
            out=set()
            for x in a:
                for y in b:
                    term=x|y
                    if term in out: out.remove(term)
                    else: out.add(term)
            return out
        def run(node):
            if isinstance(node, ast.Name): return {frozenset([int(node.id[6:])])}
            if isinstance(node, ast.Constant): return {frozenset()} if node.value else set()
            if isinstance(node, ast.UnaryOp): out=run(node.operand) ^ {frozenset()}
            else:
                a,b=run(node.left),run(node.right)
                if isinstance(node.op,ast.BitAnd): out=multiply(a,b)
                elif isinstance(node.op,ast.BitOr): out=a ^ b ^ multiply(a,b)
                else: out=a ^ b
            if len(out)>max_terms: raise ValueError('Symbolic ANF term budget exceeded')
            return out
        return tuple(sorted(sum(1 << self.sources.index(i) for i in term) for term in run(self.tree)))


def from_expressions(rules, name='Boolean network'):
    from .model import Network
    if not isinstance(rules,dict) or not rules: raise ValueError('Provide a nonempty node-to-expression map')
    names=list(rules)
    return Network(names, rules=[ExpressionRule(v,names) for v in rules.values()], name=name)
