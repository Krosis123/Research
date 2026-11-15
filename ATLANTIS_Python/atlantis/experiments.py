"""Durable local-desktop jobs with isolated, terminable quantum workers.

Single OS user, no network listener or cross-user service. SQLite stores no secrets.
"""
from pathlib import Path
from contextlib import closing
import json
import sqlite3
import uuid
import multiprocessing as mp
from queue import Empty
from time import monotonic
from datetime import datetime, timezone
from .io import network_to_dict, network_from_dict
from .analysis import CancelledError


class JobStore:
    def __init__(self,path=None):
        self.path=Path(path or Path.home()/'.atlantis'/'jobs.sqlite3')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with closing(self.connect()) as c, c:
            c.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, created TEXT, status TEXT, input TEXT, result TEXT, error TEXT)')

    def connect(self): return sqlite3.connect(self.path,timeout=10)

    def create(self,network,settings):
        from dataclasses import asdict
        identity=uuid.uuid4().hex
        with self.connect() as c:
            c.execute('BEGIN IMMEDIATE')
            if c.execute("SELECT count(*) FROM jobs WHERE status='running'").fetchone()[0]>=1:
                raise ValueError('One local quantum job may run at a time; recover interrupted jobs if needed')
            c.execute('INSERT INTO jobs VALUES (?,?,?,?,?,?)',(identity,datetime.now(timezone.utc).isoformat(),
                'running',json.dumps({'network':network_to_dict(network),'settings':asdict(settings)}),None,None))
        return identity

    def finish(self,identity,status,result=None,error=None):
        with self.connect() as c:
            c.execute('UPDATE jobs SET status=?, result=?, error=? WHERE id=?',
                      (status,json.dumps(result) if result is not None else None,error,identity))

    def list(self):
        with self.connect() as c:
            c.row_factory=sqlite3.Row
            return [dict(r) for r in c.execute('SELECT * FROM jobs ORDER BY created DESC LIMIT 100')]

    def recover(self):
        # Explicit user action after a restart, never automatically resubmit.
        with self.connect() as c:
            c.execute("UPDATE jobs SET status='interrupted',error='Previous worker interrupted; no automatic retry' WHERE status='running'")


def _worker(network,settings,queue):
    from .quantum.engine import run,Settings
    try:
        result=run(network_from_dict(network),Settings(**settings),
                   progress=lambda f,m:queue.put(('progress',f,m)))
        queue.put(('result',result))
    except Exception as e: queue.put(('error',type(e).__name__+': '+str(e)))


def execute(network,settings,progress=None,cancel=None,store=None):
    from dataclasses import asdict
    from .quantum.engine import preflight
    check=preflight(network,settings)
    if not check['eligible']: raise ValueError('; '.join(check['reasons']))
    store=store or JobStore()
    identity=store.create(network,settings)
    ctx=mp.get_context('spawn'); queue=ctx.Queue()
    process=ctx.Process(target=_worker,args=(network_to_dict(network),asdict(settings),queue),daemon=True)
    started=monotonic()
    try:
        process.start()
        while True:
            if cancel and cancel(): raise CancelledError('Quantum job cancelled')
            if monotonic()-started>settings.timeout_seconds: raise TimeoutError('Worker wall-clock deadline exceeded')
            try: msg=queue.get(timeout=.1)
            except Empty:
                if not process.is_alive(): raise RuntimeError('Quantum worker exited without a result')
                continue
            if msg[0]=='progress' and progress: progress(msg[1],msg[2])
            elif msg[0]=='error': raise RuntimeError(msg[1])
            elif msg[0]=='result':
                result=msg[1]; result['job_id']=identity
                store.finish(identity,'finished',result)
                return result
    except Exception as e:
        store.finish(identity,'cancelled' if isinstance(e,CancelledError) else 'failed',error=str(e))
        raise
    finally:
        if process.is_alive(): process.terminate()
        if process.pid: process.join(timeout=5)
        queue.close()
