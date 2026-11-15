import json
import subprocess
import sys

import numpy as np

from atlantis.classical_jobs import ClassicalJobs, make_request
from atlantis.experiments import JobStore
from atlantis.io import load_network


def test_classical_job_reruns_after_process_exit(tmp_path):
    path = tmp_path / 'jobs.db'
    network = load_network('examples/quantum/rossini4.json')
    request = make_request([network], np.zeros((1, 4), dtype=np.uint8),
                           None, 'deterministic', {}, None)
    code = """
import json
import os
import sys
from atlantis.classical_jobs import ClassicalJobs
from atlantis.experiments import JobStore

jobs = ClassicalJobs(JobStore(sys.argv[1]))
jobs.run(json.loads(sys.argv[2]), lambda *args: os._exit(17), lambda: False)
"""
    process = subprocess.run([sys.executable, '-c', code, str(path), json.dumps(request)],
                             timeout=30)
    assert process.returncode == 17
    jobs = ClassicalJobs(JobStore(path))
    identity, payload, status = jobs.recoverable()[0]
    assert status == 'running'
    output = jobs.run(json.loads(payload), lambda *args: None, lambda: False, source=identity)
    assert len(output[0][2].attractors) == 1
    assert jobs.recoverable() == []
    path.unlink()
