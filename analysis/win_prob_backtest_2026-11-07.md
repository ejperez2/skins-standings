# Chance-to-win backtest at ~9 games per team (written 2026-11-07)

Question: Eristeo showed 85% (`win_prob` 0.8532 on 2026-11-07). How did this model's
probabilities look at the same point of earlier seasons, and who actually won?

Method: `analysis/backtest_win_prob.py` re-runs the `index.qmd` simulation (Step 5.5) on the archived
snapshots (`archive/history/`, `archive/2025-26/`), picking per season the snapshot closest to 8.9 games
per team. Player-level approximation (no per-team records for old seasons; roster correlation is off below 10
league games anyway). Projection = the snapshot's `avg` (2025-26: the real `weighted_average`),
`TALENT_SD` 8.6. Past leagues had 5-6 players, so probabilities are not directly comparable with 3 players.

| Season | Model win probability, highest first | Winner |
|---|---|---|
| 2022-23 | Thomas 46%, Eristeo 19%, Kenneth 17%, Adam 13%, Brian 6% | Adam (13%) |
| 2023-24 | Matt 38%, Kenneth 24%, Eristeo 18%, Adam 9%, Brian 5%, Thomas 5% | Thomas (5%) |
| 2024-25 | Brian 43%, Thomas 19%, Matt 17%, Adam 7%, Eristeo 7%, Kenneth 6% | Brian (43%) |
| 2025-26 | Eristeo 26%, Adam 25%, Brian 23%, Matt 20%, Thomas 5%, Kenneth 2% | Adam (25%) |

Findings
- Top pick won 1 of 4; no favorite exceeded 46%. 2022-23 Thomas (46%) finished 4th; 2023-24 Thomas won from 5%.
- Over all daily snapshots with 6-14 games/team (~370 player-days, heavily overlapping, 4 seasons):
  rated 20-30% -> won ~8%; rated 35%+ -> won in 2 of 4 seasons. Weak evidence, but no sign the model is under-confident early.
- 85% is far above anything seen historically. Drivers: 8-skin lead, ~47-skin projection edge, and only 3 players.
- Caveats: `TALENT_SD` fit on one season; roster correlation is off before 10 league games.

## Is each simulated season coherent (league wins = league losses)?

No. Each team's final wins are drawn separately: normal around its projection, plus the optional shared
per-player draw, clipped to [current wins, current wins + games left]. Wins+losses = 82 holds per team (L picks use
82 - wins), but nothing ties teams together: no head-to-head pairing, and league total wins is not forced to
equal 1,230 (half of all games). Expected total is close (weighted averages sum to 1231.7 on 2026-11-07), but an
individual simulated season can total, say, 1,180 or 1,280 wins; the spread of that total is roughly 45 wins.
Missing: one team's win is another's loss, so teams (and players) are negatively correlated in reality
and are treated as independent here. Likely effect: mostly on the spread between players; a modest
issue, unquantified. Possible fixes: simulate games with pairings, or condition/rescale each simulated season
to total 1,230 wins.

## Follow-up (2026-11-08): constraint added, other ideas tested

**Added** (`MODEL_VERSION` "2026-11-08 league-total constraint"): each simulated season is conditioned on
1,230 league wins (joint-normal update by each team's covariance with the league total, roster correlation
included, then the usual clip). Run through the page's own code with `analysis/sim_harness.R`:

| Date | Before (Eristeo / Adam / Brian) | After |
|---|---|---|
| 2026-10-25 | 60.5 / 19.1 / 20.4 | 62.5 / 16.1 / 21.4 |
| 2026-11-01 | 78.7 / 12.7 / 8.6 | 80.2 / 11.0 / 8.8 |
| 2026-11-07 | 85.6 / 8.4 / 6.0 | 87.6 / 6.2 / 6.2 |
| 2026-11-07, roster corr. 0.15 forced on | 70.2 / 16.8 / 12.9 | 75.0 / 10.8 / 14.2 |

League wins per simulated season: SD ~46 before, <1 after. Adam (8 W picks, 2 L) is hurt most: his W-heavy
roster no longer gains from seasons where the whole league wins more than is possible.

Backtest (`analysis/backtest_constraint.py`, player-level, 2022-26): winner log loss, mean of seasons
0-10 games 1.912 -> 1.902, 10-20 games 1.564 -> 1.544, 20-41 games 1.525 -> 1.510; better in 3 of 4 seasons.

**Tested, not changed**
- Spread (`analysis/backtest_spread.py`): RMS z of final skins vs projection is 1.09-1.14 up to 10 games
  (a bit narrow), ~1.0 at 10-30 games, 1.2-1.4 later (but the backtest lacks the live in-season refits).
  2025-26, the only season with the real weighted average, was 0.86-0.94 early, i.e. slightly wide.
- Widening early spread by 10-30%: better in 2022-23 and 2023-24 (longshot winners), worse in 2024-25 and
  2025-26. Four winners can't pick a new `TALENT_SD`.
- Fat tails: 90 preseason team misses (2023-26) have excess kurtosis -0.55, none beyond 2.5 SD. Normal is fine.
- Not attempted: simulating the actual remaining schedule (head-to-head pairings, incl. games between
  one player's own teams). Needs a schedule scraper; the league-total constraint captures the main effect.

**Correction to an earlier heads-up.** I first said the number would drift to ~75% "even if nothing changes".
That was the effect of switching the roster correlation fully on *today*. `analysis/forward_path.R` re-runs the
page's own refit + simulation forward, with every team playing exactly at today's projected pace (~0.48 games
per team per day):

| Games/team | Page as is | Correlation from day 1 | As is, no TALENT_SD refit | Day 1, no refit |
|---|---|---|---|---|
| 8.8 (Nov 7) | 87.6 | 75.0 | 87.6 | 75.0 |
| 11.7 | 85.9 | 76.1 | 85.9 | 76.1 |
| 14.6 | 89.9 | 83.3 | 85.6 | 78.1 |
| 18.9 | 90.0 | 86.5 | 84.2 | 80.4 |
| 23.2 | 91.1 | 90.4 | 84.5 | 83.7 |
| 27.5 (mid-Dec) | 93.3 | 93.3 | 86.9 | 86.9 |

(Eristeo's Chance to Win, %. The refit columns flatter the leader because synthetic games have no luck, so the
re-estimated TALENT_SD drops; "no refit" is the more realistic stable path.)

So with stable inputs the page dips ~3 points into December, then rises; it does not fall to 75%. But the
gap between columns 2 and 3 is real: the 10->25 game ramp keeps the early number ~12 points above what the same
model with correlation from day 1 says, fading to 0 by ~25 games. A good forecast should not have a built-in
direction like that (today's number should equal the expected future number); the ramp was an empirical
compromise from 2025-26 range coverage.

Ramp vs. correlation from day 1, player-level backtest with the constraint, winner log loss (lower = better):

| | 2022-23 | 2023-24 | 2024-25 | 2025-26 | 0-10 games | 10-20 games |
|---|---|---|---|---|---|---|
| 0.15, ramp 10->25 (current) | 2.082 | 1.995 | 1.129 | 1.164 | 1.902 | 1.541 |
| 0.15 from day 1 | 1.937 | 1.913 | 1.170 | 1.202 | 1.820 | 1.517 |

Same split as widening the spread: day-1 correlation wins in the two upset seasons and loses in the two
favorite-won seasons. It's a judgment call (coherence argues for day 1).

**Changed 2026-11-08** at the league's request (prefer the assumption that gave underdogs more credit):
`RHO_RAMP` removed, roster correlation in full from opening night (`MODEL_VERSION` "2026-11-08 league-total
constraint + roster-corr from day 1"). 2026-11-07 inputs: Eristeo 75.0%, Adam 10.8%, Brian 14.2%; with stable
inputs it now rises steadily (76% at ~12 games, 80% at ~19, 87% at ~27) instead of dipping first.

## New model re-check by stage (2026-11-08, `analysis/backtest_by_stage.py`)

Player-level backtest of the live model (league-total constraint, roster correlation 0.15 from day 1).

At ~9 games per team (* = eventual winner):
- 2022-23: Thomas 40%, Eristeo 21%, Adam 16%*, Kenneth 14%, Brian 8%
- 2023-24: Matt 34%, Kenneth 24%, Eristeo 18%, Adam 10%, Thomas 7%*, Brian 7%
- 2024-25: Brian 37%*, Thomas 19%, Matt 18%, Adam 9%, Eristeo 9%, Kenneth 8%
- 2025-26: Eristeo 24%, Adam 23%*, Brian 22%, Matt 21%, Thomas 7%, Kenneth 3%

| Games/team | Winner's average prob. | Top pick won | Log loss (equal odds = 1.75) | Seasons beating equal odds |
|---|---|---|---|---|
| 9 | 21% | 1/4 | 1.72 | 2/4 |
| 15 | 26% | 2/4 | 1.49 | 2/4 |
| 20 | 31% | 2/4 | 1.26 | 3/4 |
| 25 | 29% | 1/4 | 1.28 | 4/4 |
| 30 | 21% | 0/4 | 1.58 | 2/4 |
| 41 | 22% | 0/4 | 1.73 | 2/4 |
| 50 | 33% | 1/4 | 1.36 | 3/4 |
| 70 | 70% | 4/4 | 0.36 | 4/4 |

- Early (<15 games) odds are roughly calibrated: predicted 7% -> won 10%, 17% -> 18%, 33% -> 26%. They are honest
  but carry little information: about the same as equal odds at 9 games.
- 20-25 games is the first point where the model beats equal odds in (nearly) every season.
- 30-50 games looks over-confident: the favorite (48-63% on average) lost in all four seasons (2022-23 Eristeo,
  2023-24 Matt, 2024-25 Adam, 2025-26 Matt). Snapshots given 50-75% won 10% of the time. This matches the spread
  check (RMS z 1.24-1.40 at 30-60 games). Caveat: the backtest lacks the live in-season TALENT_SD and roster
  correlation refits, which raise the spread mid-season when a season's misses run large. It also uses the source
  average for 2022-25, and covers only 4 seasons of 5-6 players.

## Reflecting weak skill in the uncertainty (2026-11-08, `analysis/backtest_uncertainty.py`, `analysis/backtest_range_coverage.py`)

Winner log loss on a held-out season (fit on 3, score the 4th; equal odds = 1.745) and how often 80% player ranges held:

| Shrink exp. | Roster corr. | Log loss (avg) | 30-50 games | Worst season | 80% range held: <15 / 15-30 / 30-50 / 50-75 games |
|---|---|---|---|---|---|
| 1.5 (live) | 0.15 (live) | 1.407 | 1.608 | 1.965 | 87 / 86 / 73 / 74% |
| 1.5 | 0.25 | 1.386 | 1.553 | 1.869 | 91 / 88 / 77 / 79% |
| 1.0 | 0.25 | 1.374 | 1.498 | 1.790 | 93 / 94 / 87 / 90% |
| 1.0 | 0.35 | 1.368 | 1.477 | 1.735 | 95 / 96 / 91 / 93% |

- Pulling final odds toward equal odds (weight fit per stage on the other seasons) was worse out of sample in every configuration.
- More uncertainty helps in 2022-23 and 2023-24 (longshot winners) and hurts a little in 2024-25 and 2025-26.
  The average favors it because log loss punishes confident misses more than it rewards confident hits.
- The cost is ranges that are too wide: beyond 0.25 the 80% ranges hold 87-96%.
- Nov 7 inputs: live 75.0 / 10.8 / 14.2 (Eristeo / Adam / Brian); corr 0.25: 71.2 / 11.2 / 17.6;
  exp 1.0 + corr 0.25: 69.8 / 11.8 / 18.5; exp 1.0 + corr 0.35: 67.6 / 11.3 / 21.1.

## Schedule simulation (2026-11-08, `analysis/sim_models.py`, `analysis/backtest_schedule.py`)

Question: the league-total constraint cut Adam's odds roughly in half because his 8 W picks moved with Eristeo's
7 L picks. Is that real, or an artifact of spreading offsetting wins across all teams instead of along the schedule?

Data: `archive/history/games_2022-26.csv` (ESPN scoreboard, regular season, All-Star and Cup finals removed). All 120
team-seasons have 82 games and final wins equal to `rosters_and_finals_2022-26.csv`. Each archived team snapshot
(142 days) gives the real record on that date and the real remaining schedule. The one shortcut: Cup knockout
matchups weren't known in advance.

Models, all with the same team-level spread (TALENT_SD 8.6, shrink 1.5) and roster correlation 0.25:
- M0: independent draws (old model).
- M1: conditioned on 1,230 league wins (live until now).
- M2: every game simulated between its two teams, strength-scale correlation 0.25.
- M2c: M2 with the strength-scale correlation calibrated so final team skins are correlated 0.25 within a roster.

Mean over seasons:

| | M0 | M1 | M2 | M2c |
|---|---|---|---|---|
| Winner log loss | 1.375 | 1.357 | 1.370 | **1.345** |
| Pairwise order log loss | 0.518 | 0.518 | **0.514** | 0.517 |
| 80% held, <15 / 15-30 / 30-50 / 50+ games | 88/87/84/77 | 88/87/83/77 | 88/85/80/**68** | 88/87/84/79 |
| 50% held | 57% | 55% | 53% | 59% |

Per season, winner log loss (M1 -> M2c): 1.832 -> 1.787, 1.320 -> 1.333, 1.185 -> 1.181, 1.090 -> 1.078.
Per season, pairwise (M1 -> M2c): .6624 -> .6590, .3574 -> .3634, .6786 -> .6733, .3719 -> .3721.

A first M2 run had a bias: random strength shifts pull expected records toward .500, which cost strong W teams and
weak L teams skins (players simulated 5-9 skins below projection). The fixed version re-centres strengths so simulated
team means are within ~0.5 wins of projections. The numbers above are after the fix.

Nov 7 inputs (page code, `analysis/sim_harness.R`): M1 70.5 / 17.7 / 11.8 (Eristeo / Brian / Adam) -> M2c 65.9 / 18.1 / 16.0.
Correlation with Eristeo: Adam 0.27 -> 0.12, Brian -0.08 -> -0.16. The constraint's effect on Adam is real but about
half the size the league-total shortcut gave it. Brian still edges Adam because Brian's outcomes are slightly
negatively tied to Eristeo's and a bit more spread out (SD ~49 vs ~45 skins).

Decision: switch the page to M2c, falling back to M1 when the schedule is unavailable. Season backfilled again.

## Four improvements tested (2026-11-08)

1. **Tie-breaking (adopted).** Ties for first in ~0.8% of simulated seasons were all credited to the first player
   alphabetically. They are now split evenly. Nov 7: Adam 16.0 -> 15.8, Brian 18.0, Eristeo 66.2.
2. **Synthetic leagues (built).** `synthetic_leagues.py` re-drafts each season into 200 three-player leagues (snake,
   drafter noise ±2 wins, matching the 2026-27 draft) and scores M1 / M2c / shrink / parameter-uncertainty variants on
   every other snapshot (14,400 forecasts per model).
   - With the live correlation (0.25), every model is badly under-confident in these leagues: 57% forecasts won 75-77%,
     and 80% ranges held 95-99%.
   - Cause: re-drafted rosters' realised correlation is about 0.06, against real rosters' 0.00 / 0.33 / 0.12 / 0.13
     (2022-26, from ~20 games) and the model's 0.25.
   - With the correlation matched (0.05), ranges are close to nominal (83/84/93/84%), but favourites still win more
     than stated (53% -> 61% at 15-30 games).
   - Summaries: `synthetic_summary_rho025.txt`, `synthetic_summary_rho005.txt`.
3. **Projections (not changed).**
   - Source weights re-fit leave-one-season-out did worse out of sample at every stage. Best weights jump between
     seasons, and equal weights only edge the current blend.
   - A stage-wise pull toward .500 (λ 0.79-0.94 early, fit on other seasons) raised held-out team error at every stage
     on average, and did worse in 3 of 4 seasons in synthetic leagues.
4. **Parameter uncertainty (not adopted).**
   - Method: per simulated season, TALENT_SD × lognormal(0, 0.28) (the season-to-season spread of the projection-error
     size in 2023-26) and ρ ~ Beta(mean 0.25, sd 0.10).
   - Synthetic leagues: better in all 4 seasons (log loss 0.7367 -> 0.7290).
   - Real leagues: worse in 3 of 4 (1.345 -> 1.352), and pairwise worse in 3 of 4.
   - It sharpens favourites, which suits the under-confident synthetic setting but not the real leagues, where
     favourites have underperformed.
