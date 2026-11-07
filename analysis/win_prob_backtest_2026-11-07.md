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

**Heads-up:** roster correlation phases in from 10 to 25 games per team (you are at ~9). With it fully on,
today's numbers would be about 75% rather than 88%, so expect the number to drift down over the next couple
of weeks even if nothing changes on the court.
