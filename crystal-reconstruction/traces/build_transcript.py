"""Reassemble a readable transcript from the raw provider response bodies and the harness trajectory.

Input (per trial, from the private run archive): run/provider/NNNNN.M.response.json (final provider response per API call)
and run/trajectory.jsonl (harness events incl. tool results). Output: transcript.jsonl and transcript.md.
Hidden reasoning is not available: Anthropic thinking blocks were returned as null and OpenAI reasoning items are encrypted;
only visible text, tool calls and tool results are reproduced. Nothing is paraphrased or edited.
"""
import json, glob, os, sys, re
from pathlib import Path

def load_tool_results(traj):
    by_id, seq = {}, []
    for line in open(traj):
        try: e = json.loads(line)
        except Exception: continue
        if e.get('event') == 'tool_result':
            r = {'call_id': e.get('call_id'), 'name': e.get('name'), 'text': e.get('text', ''), 'error': e.get('error'),
                 'image': bool(e.get('image_bytes_base64')), 't': e.get('utc_epoch')}
            by_id[r['call_id']] = r; seq.append(r)
        elif e.get('event') == 'context_compacted':
            seq.append({'compaction': True, 't': e.get('utc_epoch'), 'detail': {k: v for k, v in e.items() if k not in ('event',)}})
    return by_id, seq

def blocks_anthropic(resp):
    out = []
    for b in resp.get('content', []):
        if b['type'] == 'text' and b.get('text'): out.append({'kind': 'text', 'text': b['text']})
        elif b['type'] == 'thinking': out.append({'kind': 'thinking', 'available': bool(b.get('thinking'))})
        elif b['type'] == 'tool_use': out.append({'kind': 'tool_call', 'id': b['id'], 'name': b['name'], 'input': b['input']})
    return out

def blocks_openai(resp):
    out = []
    for it in resp.get('output', []):
        t = it.get('type')
        if t == 'message':
            txt = ''.join(c.get('text', '') for c in it.get('content', []) if c.get('type') in ('output_text', 'text'))
            if txt: out.append({'kind': 'text', 'text': txt})
        elif t == 'reasoning':
            summ = ''.join(c.get('text', '') for c in it.get('summary', []) or [])
            out.append({'kind': 'thinking', 'available': bool(summ), 'summary': summ or None})
        elif t == 'function_call':
            try: args = json.loads(it.get('arguments', '{}'))
            except Exception: args = {'_raw': it.get('arguments')}
            out.append({'kind': 'tool_call', 'id': it.get('call_id') or it.get('id'), 'name': it.get('name'), 'input': args})
    return out

def build(run_dir, out_dir, provider):
    files = sorted(glob.glob(os.path.join(run_dir, 'provider', '*.response.json')),
                   key=lambda f: [int(x) for x in os.path.basename(f).split('.')[:2]])
    by_id, seq = load_tool_results(os.path.join(run_dir, 'trajectory.jsonl'))
    t0 = None
    for line in open(os.path.join(run_dir, 'trajectory.jsonl')):
        e = json.loads(line); t0 = e.get('utc_epoch'); break
    turns, unmatched = [], 0
    for f in files:
        resp = json.load(open(f))
        n = int(os.path.basename(f).split('.')[0])
        blocks = blocks_anthropic(resp) if provider == 'anthropic' else blocks_openai(resp)
        for b in blocks:
            if b['kind'] == 'tool_call':
                r = by_id.get(b['id'])
                if r is None: unmatched += 1
                else: b['result'] = {'text': r['text'], 'error': r['error'], 'image': r['image'], 'hours': (r['t'] - t0) / 3600 if t0 and r['t'] else None}
        turns.append({'call': n, 'stop_reason': resp.get('stop_reason') or resp.get('status'), 'blocks': blocks})
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    with open(os.path.join(out_dir, 'transcript.jsonl'), 'w') as w:
        for t in turns: w.write(json.dumps(t) + '\n')
    comps = [c for c in seq if c.get('compaction')]
    md = [f'# Transcript ({provider}), {len(turns)} API calls, {sum(1 for t in turns for b in t["blocks"] if b["kind"]=="tool_call")} tool calls, {len(comps)} context compactions', '',
          'Visible model text, tool calls and tool results, in order. Hidden reasoning was not returned by the provider and is not shown. Long tool outputs are truncated in this .md; transcript.jsonl has them in full.', '']
    for t in turns:
        md.append(f'\n## Call {t["call"]}')
        for b in t['blocks']:
            if b['kind'] == 'text': md += ['', b['text']]
            elif b['kind'] == 'thinking': md += ['', '_[reasoning block: not available]_' if not b.get('available') else '_[reasoning summary]_ ' + (b.get('summary') or '')]
            elif b['kind'] == 'tool_call':
                inp = b['input']; shown = inp.get('command') or inp.get('path') or json.dumps(inp)
                if b['name'] == 'write_file': shown = f"{inp.get('path')}\n{inp.get('content','')}"
                md += ['', f'**{b["name"]}**', '```', shown[:6000] + ('\n[...truncated]' if len(shown) > 6000 else ''), '```']
                r = b.get('result')
                if r:
                    txt = r['text'] or ('[image]' if r['image'] else '')
                    md += [f'_result{" (error)" if r["error"] else ""}, t={r["hours"]:.2f} h_' if r.get('hours') is not None else '_result_', '```', txt[:3000] + ('\n[...truncated]' if len(txt) > 3000 else ''), '```']
    open(os.path.join(out_dir, 'transcript.md'), 'w').write('\n'.join(md))
    print(out_dir, 'turns', len(turns), 'unmatched tool ids', unmatched, 'compactions', len(comps))

if __name__ == '__main__':
    build(sys.argv[1], sys.argv[2], sys.argv[3])
