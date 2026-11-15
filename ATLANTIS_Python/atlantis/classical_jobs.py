"""Persist classical requests so an interrupted analysis can be rerun."""
from contextlib import closing
import json
from uuid import uuid4

import numpy as np

from .analysis import CancelledError, deterministic_analysis, map_trajectory, probabilistic_analysis
from .experiments import JobStore
from .fates import FateLogic
from .io import network_from_dict, network_to_dict


class ClassicalJobs:
    def __init__(self, store=None):
        self.store = store or JobStore()
        with closing(self.store.connect()) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS classical_jobs "
                       "(id TEXT PRIMARY KEY, request TEXT NOT NULL, status TEXT NOT NULL, source TEXT)")

    def recoverable(self):
        with closing(self.store.connect()) as db:
            return db.execute("SELECT id, request, status FROM classical_jobs "
                              "WHERE status IN ('running', 'failed', 'cancelled') "
                              "ORDER BY rowid DESC LIMIT 100").fetchall()

    def run(self, request, progress, cancel, source=None):
        identity = uuid4().hex
        with closing(self.store.connect()) as db, db:
            db.execute("INSERT INTO classical_jobs VALUES (?, ?, 'running', ?)",
                       (identity, json.dumps(request), source))
        status = 'failed'
        try:
            output = run_request(request, progress, cancel)
            status = 'finished'
            return output
        except CancelledError:
            status = 'cancelled'
            raise
        finally:
            with closing(self.store.connect()) as db, db:
                db.execute("UPDATE classical_jobs SET status=? WHERE id=?", (status, identity))
                if source and status == 'finished':
                    db.execute("UPDATE classical_jobs SET status='recovered' WHERE id=?", (source,))


def make_request(networks, states, logic, kind, settings, bounds):
    fate = None
    if logic is not None:
        fate = dict(nodes=logic.nodes, labels=logic.labels, headers=logic.headers,
                    patterns=np.where(np.isnan(logic.patterns), None, logic.patterns).tolist())
    return dict(networks=[network_to_dict(net) for net in networks],
                states=states.tolist(), fate=fate, kind=kind, settings=settings,
                bounds=None if bounds is None else bounds.tolist())


def run_request(request, progress, cancel):
    networks = [network_from_dict(net) for net in request['networks']]
    states = np.asarray(request['states'], dtype=np.uint8)
    fate = request['fate']
    logic = None if fate is None else FateLogic(**{**fate, 'patterns': np.asarray(fate['patterns'], dtype=float)})
    kind = request['kind']
    analyze = {'deterministic': deterministic_analysis, 'probabilistic': probabilistic_analysis}[kind]
    output = []
    for i, net in enumerate(networks):
        def notify(fraction, message):
            progress((i + fraction) / len(networks), f'{net.name}: {message}')

        result = analyze(net, states, fate_logic=logic, progress=notify, cancel=cancel, **request['settings'])
        if request['bounds'] is not None:
            map_trajectory(result, request['bounds'])
        output.append((net.name, kind, result))
    return output
