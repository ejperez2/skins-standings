# The forecast checked against *Forecasting: Principles and Practice* (written 2026-11-25)

Book: Hyndman & Athanasopoulos, *Forecasting: Principles and Practice*, 2nd ed. (2018), "FPP2" below; section numbers
are the book's. Question: what does the book say this forecast does well, where it falls short, and what should change?
Code for the new tests: `analysis/fpp_review/`.

**Verdict.** On method, the model already does most of what the book asks. It combines sources, simulates the
aggregate, keeps forecasts within limits, checks errors on held-out seasons by stage, and documents every assumption.
A new test from the book's residual checks also passes: the blended projection uses its information efficiently.
The shortfalls are in process, which the book's chapters on judgment and evaluation cover:

1. **The headline number is adjusted on purpose.** The default "Cautious" view uses the settings that lean toward
   the trailing players (8.6, 0.25), not the ones the evidence supports (7.2, 0.15). FPP2 4.2 and 4.7 say an
   adjustment like that belongs next to the forecast, not inside it. Today: Cautious 67 / 22 / 11
   (Eristeo / Brian / Adam), Best guess 75 / 18 / 7.
2. **The record of what the page said was being overwritten.** Through 2026-11-15, 21 of 38 days in
   `standings_history.csv` now hold a later model's re-fit, not the number the page showed. Those are fitted
   values in the book's sense, not genuine forecasts (3.3-3.4). **Fixed in this change:** `forecast_log.csv`.
3. **The model has changed 4 times in 5 weeks, each change tested on the same 4 past leagues.** FPP2 3.4 and 12.7
   warn that reusing one small test set selects for noise. Recommendation: freeze the model and score it at season
   end against the plan below.

## Scorecard

| Book principle | What the model does | Verdict |
|---|---|---|
| 1.7: a forecast is a distribution, not a number | 10,000 simulated seasons; Chance to Win plus 50% and 80% ranges | Good |
| 3.1: compare with simple benchmarks | Backtests compare with equal odds, "ignore hot start" and a record-only formula | Good. Add the preseason line held fixed to the season-end score |
| 3.3: errors should have mean zero and no autocorrelation | Bias and fat tails checked; revisions not checked until now | **Passes the new revision test** (below) |
| 3.4: judge on genuine forecasts, never on fitted values | Backtests hold out seasons; this season's history was re-fitted | **Gap, fixed:** `forecast_log.csv` |
| 3.4, 12.7: a short test set is easy to overfit | About 12 tuned settings, most chosen on 4 seasons (4 winners) | **Risk.** Freeze and pre-register (below) |
| 3.5, 11.4: check interval coverage | 80% player ranges held 87-99% in backtests | Ranges too wide, the opposite of the book's usual warning; it comes from the cautious settings |
| 4.2: keep forecasters and users apart; a forecast is not a target | The forecaster is a player; the default leans toward the trailing players "by choice" | **Gap** (recommendation 1) |
| 4.2: document, justify, review | `MODEL_SPEC.md`, dated evidence files, `model_version` saved daily | Very good |
| 4.7: adjust rarely, and only with information the model lacks | 2026-11-08 raised roster correlation to 0.25 at the league's request; 2026-11-15 kept 8.6 and 0.25 when the evidence pointed to 7.2 and 0.15 | **Gap** |
| 10.7: forecasts should add up (reconciliation) | Targets are scaled by variance to fit the games left, and every game has a winner and a loser | Good |
| 12.3: keep forecasts within limits | Logistic game model; wins bounded by games left | Good |
| 12.4: a simple average is hard to beat | 40/20/20/20 weights; your own backtest favours equal weights slightly | Small gap (recommendation 4) |
| 12.5: get prediction intervals for totals by simulation | Player totals come from simulated seasons, with correlation across games and rosters | Good: exactly the book's method |

## New test 1: are the projections efficient? (3.3, `fpp_review/revision_efficiency.py`)

The book's first check: a forecast that uses all its information leaves errors with zero mean and no
autocorrelation. For a projection revised every day, that means the latest revision should not predict either the
next revision or the remaining miss. If it does, the source moves too little (or too much).

**Archive 2022-26** (one projection per team: betting lines for 2023-26, an average of sources for 2022-23; final wins known). The test is the slope of the remaining miss on
the last revision:

| Games played | Last 7 days | Last 14 days | Last 21 days | Correlation with next 7 days' revision |
|---|---|---|---|---|
| under 20 | **+0.84** (95% CI 0.14 to 1.45) | +0.55 (−0.01 to 1.03) | +0.44 (−0.05 to 0.79) | **+0.31** |
| 20-40 | +0.07 | −0.01 | −0.03 | +0.11 |
| 40-70 | +0.12 | +0.16 | +0.10 | +0.03 |

Early in the season, betting lines move too little: a line that rose 2 wins in a week tends to keep rising. This
matches the 24-season finding that Vegas reacted only 12-21% early. From 20 games on, the lines are efficient.

**This season** (no finals yet, so only the revision-correlation part; 4-5 non-overlapping weeks × 30 teams):

| Source | Vegas | TeamRankings | ESPN BPI | CBS | DARKO | Crafted | **Weighted average** |
|---|---|---|---|---|---|---|---|
| Next week's revision vs. last week's | +0.08 | −0.19 | −0.16 | −0.23 | −0.08 | −0.10 | **−0.04** |

The rating-based sources over-react (a move tends to partly reverse), and Vegas still under-reacts slightly. The
blend sits near zero because the two errors cancel. That is the book's argument for combining (12.4) at work.
**No momentum or damping correction is warranted; the blend passes.**

## New test 2: genuine vs. re-fitted forecasts (3.4, `fpp_review/published_forecasts.py`)

Rebuilt from 1,368 commits of `standings_history.csv`. Eristeo's Chance to Win, first number published each day,
against what the file holds now:

| Date | Published | In file now | Model that published it |
|---|---|---|---|
| 2026-10-23 | 59% | 49% | before `model_version` was saved |
| 2026-11-07 | 86% | 66% | 2026-10-24 (roster corr. 0.15, league total not constrained) |
| 2026-11-08 | 65% | 66% | 2026-11-08 (schedule sim, corr. 0.25) |
| 2026-11-15 | 70% | 70% | 2026-11-08 |
| 2026-11-16 | 67% | 65% | 2026-11-15 (new fade, refit cap) |

The "To win" chart therefore shows a history the league never saw. Scoring the model at season end on that column
would reward the current model for having seen the past.

**Change made:** `index.qmd` now appends every CI run's forecast to `forecast_log.csv` (Chance to Win in all three
views, both ranges, projected and actual skins, `model_version`). Nothing rewrites that file. Runs before today
were rebuilt from git (609 rows, 38 days; `source` = `git <commit>`). New rows say `live <run id>`. Local renders
don't write to it. `.github/workflows/publish.yml` commits it with the other history files.

## Recommendations

**1. Make Best guess the headline, and show Cautious as the scenario (4.2, 4.7). Not changed: the league chose the
current default (2026-11-08).** The book is explicit that a forecast is "predicting the future as accurately as
possible". Leaning a forecast toward an outcome the users prefer is what it calls confusing forecasts with targets.
Tourism Forecasting Committee is its cautionary example. The evidence for each lean:
- `TALENT_SD` 8.6 was fit on 2025-26, the fourth-worst season for preseason lines in 24. The 24-season value is 7.2.
- Roster correlation 0.25 sits at the top of the real-roster interval (0.08-0.18). This season it is 0.00 so far.
- The 80% ranges hold 87-99% in backtests where the book's target is 80%.

What argued for 0.25 (better winner log loss in 2 upset seasons out of 4) rests on 4 data points. That is the
small-sample situation 12.7 warns about. Note the direction: the lean works *against* the forecaster's own number,
so it is not self-serving. But it is still a planned bias, and the book's fix is to show it as a scenario. The page
already computes both views, so this is a small change: swap which one the table and chart show by default, and relabel.

**2. Freeze the model until season end, and score it against a plan written now (3.4, 4.2).** Four
model changes in five weeks, each picked on the same 4 leagues, is the overfitting pattern of 3.4. Changes
should wait for information the model lacks, such as a major injury model or a known data fault (4.7: "use
adjustments sparingly"). Season-end scoring, from `forecast_log.csv`, first run of each listed day:
- Checkpoints Dec 1, Jan 1, Feb 1, Mar 1 and Apr 1, for both views:
  - log score of the eventual winner (one outcome, so a sanity check only);
  - 50% and 80% range hits per player (15 checks per view per range);
  - player z-scores, final minus projected over the implied SD.
- Team level, from `team_projection_history.csv`: RMSE of each source and of the blend at each checkpoint.
  Compare with the preseason line held fixed and with record pace (benchmarks, 3.1).
- Decide next season's defaults from this score added to the 4 past leagues, not from re-tuning.

**3. Keep the blend; no momentum or damping correction (3.3).** Test 1 shows the blend's revisions are
uncorrelated. The early under-reaction of betting lines is real, but the 60% non-Vegas share already offsets it.

**4. Optional: equal source weights (12.4).** `analysis/backtest_source_weights.py` (2023-26, held out by season)
already shows:
- Equal weights at or below the current RMSE on average at every stage: 19.18 vs 19.46, 16.05 vs 16.27,
  13.61 vs 13.64 and 7.27 vs 7.47 skins.
- Vegas alone was the worst single source on average.

The book's reading: a simple average is hard to beat, and extra weight on one source needs evidence, which here is
missing. The effect today is tiny: Eristeo −0.5, Brian +0.4, Adam −1.2 projected skins
(`fpp_review/equal_weights_today.py`). It also slightly worsens this season's revision test (−0.08 vs −0.04).
Leave it for next season unless the model is being changed anyway.

## Reproduce

```bash
git fetch --unshallow                                                       # the rebuild needs full history
python3 analysis/fpp_review/revision_efficiency.py
python3 analysis/fpp_review/equal_weights_today.py
python3 analysis/fpp_review/published_forecasts.py /tmp/rebuilt_log.csv    # compare with forecast_log.csv
python3 analysis/backtest_source_weights.py
```
