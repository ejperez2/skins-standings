# Summarise league-transplant results (transplant.py output). Usage: tp_report.py results.csv [gapEB gapEA]
import numpy as np, pandas as pd, sys
R = pd.concat([pd.read_csv(f) for f in sys.argv[1].split(',')]); GEB, GEA = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else (53.0, 50.1)
rng = np.random.default_rng(5)
def boot(d, f, n=2000):
    ss = d.season_end.unique(); g = {s: d[d.season_end == s] for s in ss}
    v = [f(pd.concat([g[s] for s in rng.choice(ss, len(ss))])) for _ in range(n)]; return np.percentile(v, [2.5, 97.5])
for st, d in R.groupby('stage'):
    print('\n===== stage %.1f games/team: %d seasons x %d leagues each =====' % (st, d.season_end.nunique(), d.jit.nunique()))
    e = d[d.jit == 0]
    print('exact transplant: E-slot won %d of %d seasons; model gave it %.0f%% on average (range %.0f-%.0f%%)' % (e.won_E.sum(), len(e), 100 * e.wp_E.mean(), 100 * e.wp_E.min(), 100 * e.wp_E.max()))
    f = lambda q: q.won_E.mean(); lo, hi = boot(d, f)
    print('all leagues: E-slot won %.0f%% (season-bootstrap 95%% CI %.0f-%.0f%%) vs model %.0f%%' % (100 * f(d), 100 * lo, 100 * hi, 100 * d.wp_E.mean()))
    # calibration over all three slots
    L = pd.concat([pd.DataFrame(dict(season_end=d.season_end, p=d['wp_' + k], won=d['won_' + k], pit=d['pit_' + k], in80=d['in80_' + k], in50=d['in50_' + k],
                                     z=(d['act_' + k] - d['mu_' + k]) / d['sd_' + k])) for k in 'ABE'])
    L['bin'] = pd.cut(L.p, [0, .1, .2, .35, .5, .65, .8, 1.0])
    print(L.groupby('bin', observed=True).agg(n=('p', 'size'), model=('p', 'mean'), won=('won', 'mean')).round(3).to_string())
    ll = lambda q: -np.mean(np.log(np.clip(np.where(q.won_E > 0, q.wp_E, np.where(q.won_B > 0, q.wp_B, q.wp_A)), 1e-3, 1)))
    # log loss under a power-sharpened forecast p^a / sum: a>1 means the model was under-confident
    def ll_a(q, a):
        P = np.c_[q.wp_A, q.wp_B, q.wp_E]**a; P /= P.sum(1, keepdims=True); Wn = np.c_[q.won_A, q.won_B, q.won_E]; return -np.mean(np.log(np.clip((P * (Wn > 0)).sum(1), 1e-4, 1)))
    As = np.arange(.4, 4.01, .1); best = lambda q: As[np.argmin([ll_a(q, a) for a in As])]
    lo, hi = boot(d, best, 400)
    print('winner log loss: model %.3f, equal odds %.3f; best sharpening exponent %.1f (95%% CI %.1f-%.1f; 1 = calibrated, >1 = model under-confident)' % (ll(d), np.log(3), best(d), lo, hi))
    print('player totals: RMS z %.2f; 80%% range held %.0f%%, 50%% range held %.0f%%; team-level mean z^2 %.2f, 80%% held %.0f%%' % (np.sqrt((L.z**2).mean()), 100 * L.in80.mean(), 100 * L.in50.mean(), d.team_z2.mean(), 100 * d.team_in80.mean()))
    lo, hi = boot(L, lambda q: np.sqrt((q.z**2).mean()))
    print('   RMS z 95%% CI %.2f-%.2f' % (lo, hi))
    for k in ['EB', 'EA', 'BA']:
        er = d['dact_' + k] - d['dmu_' + k]; z = er / d['dsd_' + k]
        print('   gap %s: projected %.0f avg, mean miss %+.1f (season se %.1f), empirical SD %.1f vs model SD %.1f, RMS z %.2f' % (k, d['dmu_' + k].mean(), er.mean(),
              er.groupby(d.season_end).mean().std() / np.sqrt(d.season_end.nunique()), er.std(), d['dsd_' + k].mean(), np.sqrt((z**2).mean())))
    vr_p = (L.z**2).mean(); vr_t = d.team_z2.mean()
    print('   implied roster correlation (model uses 0.25): %.2f' % (((1 + 9 * .25) * vr_p / vr_t - 1) / 9))
    if abs(st - 12.6) < 1:
        zb, za = (d.dact_EB - d.dmu_EB) / d.dsd_EB, (d.dact_EA - d.dmu_EA) / d.dsd_EA
        for lab, sdB, sdA in [('scaled to today (model SDs 65.5 / 56.2)', 65.5, 56.2)]:
            d = d.assign(ok=((GEB + zb * sdB > 0) & (GEA + za * sdA > 0)).astype(float)); lo, hi = boot(d, lambda q: q.ok.mean())
            print("TODAY'S GAPS (+%.0f over Brian, +%.0f over Adam) hit with each past season's standardized miss: Eristeo stays first in %.0f%% (95%% CI %.0f-%.0f%%); exact transplant only: %d of %d" % (GEB, GEA, 100 * d.ok.mean(), 100 * lo, 100 * hi, d[d.jit == 0].ok.sum(), (d.jit == 0).sum()))
        d = d.assign(ok2=((GEB + d.dact_EB - d.dmu_EB > 0) & (GEA + d.dact_EA - d.dmu_EA > 0)).astype(float)); lo, hi = boot(d, lambda q: q.ok2.mean())
        print('   same with raw misses in skins: %.0f%% (95%% CI %.0f-%.0f%%)' % (100 * d.ok2.mean(), 100 * lo, 100 * hi))
