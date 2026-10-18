"""Run a list of jobs (a 'matrix': e.g. every message x every character, every area x every
character x every input policy) on several processes.  Each worker builds its own emulator;
jobs are plain tuples handed to a function of the game profile.

    results = run_matrix('profiles.popful_mail', 'job_message', jobs, workers=2, init_args=(rom,))

The profile module must define `init_worker(*init_args)` (load ROM, base states...) and the job
function `job_x(job) -> dict` returning {'job': ..., 'issues': [...], 'shots': {...}, ...}."""
import importlib, multiprocessing as mp, time, sys, os, json

_P = None
def _init(modname, init_args, path, init_fn='init_worker'):
    global _P
    if path not in sys.path: sys.path.insert(0, path)
    _P = importlib.import_module(modname)
    getattr(_P, init_fn)(*init_args)

def _call(args):
    fn, job = args
    t = time.time()
    try:
        r = getattr(_P, fn)(job)
    except Exception as ex:                         # a tool failure is reported, never fatal to the run
        import traceback
        r = {'job': job, 'issues': [{'kind': 'tool_error', 'severity': 'high',
                                     'detail': repr(ex) + ' ' + traceback.format_exc()[-300:]}]}
    r['seconds'] = round(time.time() - t, 1)
    return r

def run_matrix(modname, fn, jobs, workers=2, init_args=(), progress=None, path=None, init_fn='init_worker'):
    path = path or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = []
    ctx = mp.get_context('fork')
    with ctx.Pool(workers, initializer=_init, initargs=(modname, init_args, path, init_fn)) as pool:
        for k, r in enumerate(pool.imap_unordered(_call, [(fn, j) for j in jobs], chunksize=1)):
            out.append(r)
            if progress and (k + 1) % progress == 0:
                bad = sum(1 for x in out if x.get('issues'))
                print('  %d/%d done, %d with issues' % (k + 1, len(jobs), bad), flush=True)
    return out

def save(results, path):
    json.dump(results, open(path, 'w'), indent=0, default=str)
