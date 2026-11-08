# Chance to Win: model specification

Current as of `MODEL_VERSION` "2026-11-08 schedule sim + roster-corr 0.25 from day 1 + split ties".
Code: Step 5.5 of `index.qmd`. Evidence for every choice: `analysis/win_prob_backtest_2026-11-07.md` and the
README section "Chance to Win and Likely Range".

## What kind of model

A **Monte Carlo season simulation on a Bradley–Terry (logistic paired-comparison) game model**. Team strengths are
**implied by consensus win projections** rather than estimated by the model, and projection error is a **random effect
with a one-factor (per-roster) correlation structure**. It does not rate teams itself. It adds calibrated uncertainty
around the weighted-average projection and turns it into skins outcomes for this league.

## Inputs (every run)

| Symbol | Meaning | Source |
|---|---|---|
| *Wᵢ, Lᵢ* | team *i*'s current record | ESPN standings (JSON feed and HTML page; whichever has more games) |
| *nᵢ* | games left, 82 − *Wᵢ* − *Lᵢ* | |
| *Pᵢ* | projected final wins: weighted average of Vegas 40 / TeamRankings 20 / ESPN BPI 20 / CBS 20, re-normalised over available sources, clipped to [*Wᵢ*, *Wᵢ* + *nᵢ*]. Vegas is left out when no line has moved for 3 days; a missing line is carried at most 5 days | `WEIGHTS`, `VEGAS_FREEZE_DAYS`, `VEGAS_MAX_CARRY_DAYS` |
| owner(*i*), side*ᵢ* | drafting player; +1 for a W pick, −1 for an L pick | `draft_data` |
| games *g* = (home, away) | remaining regular-season schedule (NBA Cup final excluded) | ESPN scoreboard, one request per month |
| *uᵢ* | team-games not yet scheduled (normally the 2 NBA Cup games per team until December) = *nᵢ* − listed games | |

## Specification

1. **Game model.** P(home wins) = logistic(*s*_home − *s*_away + *h*), home edge *h* = 0.22 (home teams won 55.5% of
   2022-26 games). An unscheduled game is against a league-average side: P(win) = logistic(*sᵢ*).
2. **Base strengths.** Solve for *sᵢ* so expected remaining wins equal *Pᵢ* − *Wᵢ* for every team (Newton iterations).
   Targets are adjusted, in proportion to each team's game variance, so they add up to the games left.
3. **Target uncertainty per team.** Var(final winsᵢ) = *nᵢ rᵢ(1 − rᵢ)* + *τᵢ²*:
   - The first term is game luck, with *rᵢ* = (*Pᵢ* − *Wᵢ*)/*nᵢ*.
   - *τᵢ* = *T*·(*nᵢ*/82)^1.5 is projection error.
   - *T* = 8.6 (fit on 2025-26). Once teams have played 12+ games since opening night, *T* blends toward a method-of-moments
     estimate from this season's misses (opening snapshot vs today, clamped 4-14), with weight min(1, games played / 41).
4. **Random effects (one draw per team per simulated season).** *zᵢ* = √(1 − ρₛ)·εᵢ + √ρₛ·sideᵢ·*v*_owner(*i*), with
   ε and *v* iid N(0, 1). Strength shift δᵢ = *k*·*τᵢ*·*zᵢ* / *Vᵢ*, where *Vᵢ* = Σ p(1 − p) over team *i*'s remaining
   games, so the shift is about *τᵢ zᵢ* wins.
5. **Calibration (every run).**
   - *k*: summed team variance of simulated final wins matches step 3.
   - Re-centring: random shifts pull expected records toward .500 (the logistic flattens at the ends), so base strengths
     are re-centred until simulated mean wins match *Pᵢ* (within 0.03 wins on the calibration draws).
   - ρₛ (strength scale) is tuned so that teams on one roster finish with mean pairwise correlation ρ in final skins.
     ρ = 0.25 (`ROSTER_RHO_FLOOR`). From the first snapshot with 20+ games, ρ can blend upward toward this season's
     estimate (weight games played / 41, capped at 0.6) but never below 0.25. ρₛ is about 0.37 in November.
6. **Simulation.** 10,000 seasons, seeded by the date. Each remaining game is a Bernoulli draw.
   - Final skins: wins for W picks, 82 − wins for L picks, summed over each player's 10 teams.
   - **Chance to Win** = share of seasons a player finishes first, with ties split evenly.
   - **Likely ranges** = 10th–90th and 25th–75th percentiles of simulated totals.
7. **Fallback** (schedule unreadable, or listed games don't fit the standings: any team with more listed than left, or
   more than 6 unscheduled).
   - Final wins ~ N(*Pᵢ*, *nᵢ rᵢ(1 − rᵢ)* + *τᵢ²*) with the same roster factor.
   - Each season is conditioned on 1,230 league wins (joint-normal update by covariance with the league total), then
     clipped to possible values.
   - `model_version` gets " [league-total fallback]".

Saved each day in `standings_history.csv`: `win_prob`, `range_lo/hi` (80%), `range_lo50/hi50`, `model_version`,
`model_talent_sd`, `model_rho`, `model_rho_in_use`.

## Assumptions

| # | Assumption | Status |
|---|---|---|
| 1 | The weighted-average projection is unbiased; the model never adjusts it | Tested Nov 2026: re-fit source weights and a pull toward .500 both did worse on held-out seasons |
| 2 | One strength error per team per simulated season; no drift with injuries or trades | Not tested |
| 3 | Games independent given strengths (no rest, travel or back-to-back effects) | Not tested |
| 4 | One home edge for every team, all season | Estimated from 2022-26 overall |
| 5 | Errors normal on the strength scale | Tested: 90 preseason team misses, excess kurtosis −0.55, none beyond 2.5 SD |
| 6 | Projection error shrinks as (games left / 82)^1.5 | Fit on 2025-26; 4-season re-fit no better out of sample |
| 7 | Same base uncertainty *T* for every team | Not tested (archive has one source per team, so source disagreement can't be used) |
| 8 | One shared factor per roster, equal for every pair of its teams, ρ = 0.25 | Level backtested on real leagues. Real rosters' realised correlation was 0.00 / 0.33 / 0.12 / 0.13 (2022-26, from ~20 games), so 0.25 leans toward underdogs; kept by choice |
| 9 | Players affect each other only through games their teams play | Schedule model beat the league-total shortcut on real leagues |
| 10 | No late-season tanking or resting | Checked: last ~20 games, sub-30-win teams −0.7 wins vs projection, 55+ teams +1.1; inconsistent by season |
| 11 | *T* and ρ are known (no parameter uncertainty) | Tested Nov 2026: drawing them per season helped in synthetic leagues, hurt slightly in real ones; not adopted |
| 12 | Ties for first split evenly | No league tiebreak rule known |
| 13 | Unscheduled Cup games are against a league-average side | Affects 2 games per team until December |

## Known limitations

- Early-season skill is low. At ~9 games the model is about as good as equal odds on past seasons; it first beats them
  consistently around 20-25 games per team. Mid-season (30-50 games), favourites have underperformed in real leagues.
- Evidence comes from 4 seasons of 5-6 player leagues. Synthetic leagues (`analysis/synthetic_leagues.py`) multiply
  roster combinations but share the same team outcomes, and re-drafted rosters lack real drafters' clustering
  (realised roster correlation about 0.06 vs about 0.15 for real rosters). They test team-level changes, not ρ.
