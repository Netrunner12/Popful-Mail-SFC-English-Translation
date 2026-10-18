"""Turn run results into a bug log: a JSON list plus an HTML page with a picture per finding.
Generic.  A result is {'job': ..., 'title': str, 'issues': [...], 'shots': {name: png_path}}."""
import html, json, os, collections

SEV = {'high': 0, 'medium': 1, 'low': 2}

def flatten(results):
    rows = []
    for r in results:
        for i in r.get('issues', []):
            rows.append(dict(i, title=r.get('title', str(r.get('job'))), shot=i.get('shot') or next(iter(r.get('shots', {}).values()), None),
                             job=r.get('job')))
    rows.sort(key=lambda x: (SEV.get(x['severity'], 3), x['kind'], x['title']))
    return rows

def write(results, out_dir, title, notes=''):
    os.makedirs(out_dir, exist_ok=True)
    rows = flatten(results)
    json.dump(rows, open(os.path.join(out_dir, 'bugs.json'), 'w'), indent=1, default=str)
    counts = collections.Counter((r['severity'], r['kind']) for r in rows)
    h = ['<!doctype html><meta charset="utf-8"><title>%s</title>' % html.escape(title),
         '<style>body{font:14px system-ui;margin:16px;background:#fff;color:#222}'
         'img{image-rendering:pixelated;width:384px;border:1px solid #ccc}'
         '.r{display:flex;gap:12px;align-items:flex-start;margin:10px 0;padding-bottom:10px;border-bottom:1px solid #eee}'
         '.high{color:#b00}.medium{color:#a60}.low{color:#666}</style>',
         '<h1>%s</h1><p>%d runs, %d findings</p><p>%s</p><ul>' % (html.escape(title), len(results), len(rows), html.escape(notes))]
    for (sev, kind), n in sorted(counts.items(), key=lambda x: (SEV.get(x[0][0], 3), x[0][1])):
        h.append('<li class="%s">%s: %s × %d</li>' % (sev, sev, kind, n))
    h.append('</ul>')
    for r in rows:
        img = '<img src="%s">' % html.escape(os.path.relpath(r['shot'], out_dir)) if r.get('shot') else ''
        h.append('<div class="r">%s<div><b class="%s">%s — %s</b><br>%s<br><small>%s</small></div></div>' % (
            img, r['severity'], r['severity'], html.escape(r['kind']), html.escape(r['title']), html.escape(r['detail'])))
    open(os.path.join(out_dir, 'report.html'), 'w').write('\n'.join(h))
    return rows
