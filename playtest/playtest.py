"""Play-test a build and write a bug log.

  python3 playtest.py ROM static                      code/text checks, no emulation (seconds)
  python3 playtest.py ROM messages [IDS...]           every message (or the listed ones) x every hero
  python3 playtest.py ROM explore [--frames N] [--save X.srm]   every area x hero x input policy, English vs original
  python3 playtest.py ROM states FILE...              user's snes9x save states x hero x policy
  python3 playtest.py ROM all                         static + messages + explore

Output: playtest/out/<crc>/<command>/report.html and bugs.json (+ shots/)."""
import sys, os, json, time, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from snestest import runner, report
from profiles import popful_mail as P

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rom'); ap.add_argument('cmd'); ap.add_argument('rest', nargs='*')
    ap.add_argument('--chars', default='0,1,2'); ap.add_argument('--workers', type=int, default=2)
    ap.add_argument('--frames', type=int, default=3600); ap.add_argument('--save')
    ap.add_argument('--areas', default='')
    a = ap.parse_args()
    rom = os.path.abspath(a.rom); chars = [int(c) for c in a.chars.split(',')]
    init = P.prepare(rom); tag = P.crc(rom)
    base_out = os.path.join(HERE, 'out', tag); os.makedirs(base_out, exist_ok=True)
    cmds = ['static', 'messages', 'explore'] if a.cmd == 'all' else [a.cmd]
    for cmd in cmds:
        out = os.path.join(base_out, cmd); os.makedirs(out, exist_ok=True)
        t = time.time()
        if cmd == 'static':
            res = [P.static_checks(rom)]; print('static:', res[0]['summary'])
        elif cmd == 'messages':
            ids = a.rest if a.rest and cmd == a.cmd else sorted(json.load(open(rom + '.msgs.json')))
            meta = json.load(open(init[2]))
            skipped = [m for m in ids if P.context_only(m, meta)]
            ids = [m for m in ids if not P.context_only(m, meta)]
            if skipped: print('messages: %d shop/menu texts need their own menu running; not swept here' % len(skipped))
            entries = set(json.load(open(os.path.join(os.path.dirname(init[2]), 'entries.json'))))
            if not (a.rest and cmd == a.cmd):
                frag = [m for m in ids if m not in entries]; ids = [m for m in ids if m in entries]
                print('messages: %d started by the game; %d more are reached only through them' % (len(ids), len(frag)))
            jobs = [(m, c) for m in ids for c in chars]
            print('messages: %d jobs' % len(jobs))
            res = runner.run_matrix('profiles.popful_mail', 'job_message', jobs, a.workers, init[:3] + (out,), progress=200, path=HERE)
        elif cmd == 'explore':
            areas = [tuple(map(int, x.split('/'))) for x in a.areas.split(',')] if a.areas else \
                    [(ar, s) for ar in range(6) for s in range(0, 14)]
            jobs = [(ar, s, c, pol, a.frames, rk) for ar, s in areas for c in chars for pol in ('walk', 'talk')
                    for rk in ('en', 'jp')]
            print('explore: %d jobs' % len(jobs))
            res = runner.run_matrix('profiles.popful_mail', 'job_explore', jobs, a.workers, (rom, init[2], out, a.save),
                                    progress=50, path=HERE, init_fn='init_explore')
            res = compare_roms(res)
        elif cmd == 'states':
            jobs = [(os.path.abspath(f), c, pol, a.frames) for f in a.rest for c in chars for pol in ('talk', 'walk', 'menu')]
            res = runner.run_matrix('profiles.popful_mail', 'job_state', jobs, a.workers, (rom, init[2], out),
                                    path=HERE, init_fn='init_state')
        if cmd == 'messages' and not (a.rest and cmd == a.cmd):
            reached = {v for r in res for v in r.get('visited', [])}
            missed = sorted(set(json.load(open(rom + '.msgs.json'))) - reached - set(skipped))
            json.dump(missed, open(os.path.join(out, 'not_reached.json'), 'w'))
            print('messages: %d texts seen on screen, %d never reached by this sweep (not_reached.json)' % (len(reached), len(missed)))
        runner.save(res, os.path.join(out, 'results.json'))
        rows = report.write(res, out, 'Popful Mail play-test: %s (%s)' % (cmd, tag))
        print('%s: %d runs, %d findings, %.0f s -> %s' % (cmd, len(res), len(rows), time.time() - t, os.path.join(out, 'report.html')))

def compare_roms(res):
    """keep English-only problems as bugs; problems the original ROM has too are test artefacts
    (e.g. warping somewhere the game never expects).  Both outcomes are recorded."""
    by = {}
    for r in res:
        ar, s, c, pol, fr, rk = r['job']; by.setdefault((ar, s, c, pol), {})[rk] = r
    out = []
    for k, d in by.items():
        en, jp = d.get('en'), d.get('jp')
        if not en: continue
        jp_kinds = {i['kind'] for i in (jp or {}).get('issues', [])}
        for i in en['issues']:
            if i['kind'] in ('crash', 'black_screen', 'frozen'):
                if i['kind'] in jp_kinds:
                    i['severity'] = 'info'; i['detail'] += ' — the original Japanese ROM does the same here (test artefact)'
                else:
                    i['detail'] += ' — the original Japanese ROM does NOT (translation bug?)'
        en['messages_jp'] = (jp or {}).get('messages', [])
        out.append(en)
    return out

if __name__ == '__main__':
    main()
