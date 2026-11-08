# Three ways to simulate the rest of a season, sharing one team-level spread (the live model's):
#   sd_i^2 = left_i * p_i * (1 - p_i) + (TALENT_SD * (left_i / 82)^1.5)^2, roster correlation RHO (signed by pick)
# M0 "independent": each team's final wins drawn on its own (pre-Nov 2026 model)
# M1 "league total": M0 conditioned so every simulated season has 1,230 wins (live since 2026-11-08)
# M2 "schedule": every remaining game simulated between its two teams. Team strengths (logit scale, plus a home
#     edge) are fit so each team's expected final wins equal its projection; each simulated season shifts each
#     team's strength by a talent miss (same TALENT_SD shrink and roster correlation as M0), scaled so the
#     team-level spread matches M0's. Wins and losses are coherent game by game.
import numpy as np
TALENT_SD, EXP = 8.6, 1.5
def team_inputs(W, L, proj):
    left = np.maximum(82 - (W + L), 0).astype(float)
    proj = np.clip(proj, W, W + left)
    rate = np.where(left > 0, np.clip((proj - W) / np.maximum(left, 1e-9), .01, .99), .5)
    tsd = TALENT_SD * (left / 82) ** EXP
    sd = np.sqrt(left * rate * (1 - rate) + tsd ** 2)
    return left, proj, rate, tsd, sd
def roster_z(pid, side, rho, n, rng):
    z = rng.standard_normal((len(pid), n)); u = rng.standard_normal((pid.max() + 1, n))
    return np.sqrt(1 - rho) * z + np.sqrt(rho) * side[:, None] * u[pid]
def sim_m0_m1(W, L, proj, pid, side, rho, n, rng, constrain):
    left, proj, rate, tsd, sd = team_inputs(W, L, proj)
    miss = sd[:, None] * roster_z(pid, side, rho, n, rng)
    if constrain:
        same = (pid[:, None] == pid[None, :]) & ~np.eye(len(pid), dtype=bool)
        C = np.diag(sd ** 2) + rho * np.outer(side * sd, side * sd) * same
        excess = (proj[:, None] + miss).sum(0) - 41 * len(pid)
        miss = miss - np.outer(C.sum(1) / C.sum(), excess)
    return np.clip(proj[:, None] + miss, W[:, None], (W + left)[:, None])
def sigmoid(x): return 1 / (1 + np.exp(-x))
def fit_strengths(W, proj, hi, ai, phantom, h, iters=200):
    """Strengths s so expected remaining wins = proj - W. hi/ai: team index of home/away per remaining game.
    phantom[i]: games team i still has against an opponent not yet scheduled (league-average, neutral)."""
    T = len(W); target = proj - W
    G = len(hi) + phantom.sum() / 2.0                  # remaining games (phantom games pair off on average)
    s = np.zeros(T)
    for _ in range(iters):
        p = sigmoid(s[hi] - s[ai] + h)
        E = np.bincount(hi, p, T) + np.bincount(ai, 1 - p, T) + phantom * sigmoid(s)
        V = np.bincount(hi, p * (1 - p), T) + np.bincount(ai, p * (1 - p), T) + phantom * sigmoid(s) * (1 - sigmoid(s))
        # targets must add to the games left; spread any gap by each team's variance
        tgt = target + (G - target.sum()) * V / V.sum()
        step = (tgt - E) / np.maximum(V, 1e-6)
        s = s + np.clip(step, -1, 1); s -= s.mean()
        if np.abs(tgt - E).max() < 1e-4: break
    return s, V, tgt
def sim_m2(W, L, proj, pid, side, rho, n, rng, hi, ai, phantom, h=0.22, k=None):
    left, proj, rate, tsd, sd = team_inputs(W, L, proj)
    s, V, tgt = fit_strengths(W, proj, hi, ai, phantom, h)
    def run(kk, n_, rng_):
        nonlocal s
        delta = kk * tsd[:, None] * roster_z(pid, side, rho, n_, rng_) / np.maximum(V, 1e-6)[:, None]
        sh = s[:, None] + delta
        p = sigmoid(sh[hi] - sh[ai] + h)                               # games x sims
        hw = (rng_.random(p.shape) < p)
        wins = np.zeros((len(W), n_))
        np.add.at(wins, hi, hw); np.add.at(wins, ai, ~hw)
        if phantom.any():                                              # unscheduled games vs a league-average side
            pp = sigmoid(sh)
            wins += rng_.binomial(phantom[:, None].astype(int).repeat(n_, 1), pp)
        return W[:, None] + wins
    if k is None:   # calibrate the talent scale so the summed team variance matches M0's
        r = np.random.default_rng(12345); n0 = 3000
        v0 = run(0.0, n0, r).var(1).sum(); v1 = run(1.0, n0, r).var(1).sum()
        target_talent = (sd ** 2).sum() - v0
        k = np.sqrt(max(target_talent, 0) / max(v1 - v0, 1e-9))
    # Random strength shifts pull expected records toward .500 (the logistic curve flattens at the ends), so
    # re-centre each team's base strength until its simulated mean wins match its projection again.
    for _ in range(4):
        m = run(k, 3000, np.random.default_rng(4321)).mean(1) - W
        gap = tgt - m
        if np.abs(gap).max() < 0.05: break
        s = s + gap / np.maximum(V, 1e-6)
    return run(k, n, rng), k
def player_outcomes(final_w, pid, side, n_players):
    sk = np.where(side[:, None] == 1, final_w, 82 - final_w)
    tot = np.vstack([sk[pid == i].sum(0) for i in range(n_players)])
    win = (tot == tot.max(0)); win = win / win.sum(0)
    return tot, win.mean(1)

def roster_corr(final_w, pid, side):
    """Mean correlation of skins outcomes between teams on the same roster, across simulated seasons."""
    sk = side[:, None] * final_w
    c = np.corrcoef(sk); same = (pid[:, None] == pid[None, :]) & ~np.eye(len(pid), dtype=bool)
    return np.nanmean(c[same])
def sim_m2_cal(W, L, proj, pid, side, rho_target, n, rng, hi, ai, phantom, h=0.22, iters=3, n_pilot=3000):
    """M2 with the strength-space roster correlation calibrated so teams on one roster end up as correlated
    (in final skins) as rho_target, i.e. the same meaning rho has in M0/M1."""
    rho_s = min(0.95, rho_target * 1.6)
    for _ in range(iters):
        r = np.random.default_rng(777)
        fw, k = sim_m2(W, L, proj, pid, side, rho_s, n_pilot, r, hi, ai, phantom, h)
        eff = roster_corr(fw, pid, side)
        if not np.isfinite(eff) or eff <= 0: break
        rho_s = float(np.clip(rho_s * rho_target / eff, 0, 0.95))
    fw, k = sim_m2(W, L, proj, pid, side, rho_s, n, rng, hi, ai, phantom, h)
    return fw, k, rho_s
