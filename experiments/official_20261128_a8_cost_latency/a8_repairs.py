import glob, json, os, sys, collections
REPO = sys.argv[1]
for alias in ['gpt-oss-or-grounded', 'deepseek-grounded', 'gpt-oss-or-parser-only']:
    kinds = collections.Counter(); zero0 = 0; err0 = 0; rep = 0; fin = collections.Counter(); outc = collections.Counter()
    ex = []
    for p in glob.glob(os.path.join(REPO, 'benchmarks', '*', 'official', 'llm_outputs', alias, '*', 'provenance.json')):
        d = json.load(open(p))
        for pi in (d.get('grounded') or {}).get('per_invariant', []):
            outc[pi.get('outcome')] += 1
            r = pi.get('rounds', [])
            if len(r) > 1:
                rep += 1
                r0 = r[0]
                if r0.get('n_actions', 0) == 0: zero0 += 1
                if r0.get('errors'): err0 += 1
                for e in r0.get('errors', [])[:3]:
                    kinds[str(e)[:70]] += 1
                fin[len(r) - 1] += 1
                if len(ex) < 2: ex.append(r)
    print('==', alias, '| outcomes', dict(outc), '| repaired', rep, '| round0 empty', zero0, '| round0 with errors', err0, '| repair rounds used', dict(fin))
    for k, v in kinds.most_common(6): print('   %3d  %s' % (v, k))
