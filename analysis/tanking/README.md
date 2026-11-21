# Tanking study (not part of the webpage)

Is tanking getting better or worse under the new lottery (3 balls for non-play-in teams outside the bottom 3; 2 for the
bottom 3 and for play-in seeds 9-10; fewer for seeds 7-8)?

## Data (`data/`, logged daily by `.github/workflows/tanking-log.yml`)
| File | What |
|---|---|
| `lottery_odds.csv` | Basketball-Reference projected lottery odds for all 30 teams (balls 0-3, bottom-3 %), one snapshot per day. The site keeps no history. |
| `injuries.csv` | ESPN injury report, one snapshot per day (ESPN only shows the current report). |
| `<season>/games.csv` | Final scores, ESPN event ids. Season = year it ends. |
| `<season>/box.csv` | Per player per game: starter, DNP + reason, minutes, points, +/-. |
| `<season>/stints.csv` | Who was on the floor when (game seconds), with the team's margin and win probability at entry. Rebuilt from play-by-play substitutions; matches box-score minutes to ~15 s. |
| `<season>/flow.csv` | Score margin and ESPN home win probability at each game minute. |
| `athletes.csv` | Birth date (d/m/y), draft, experience. |

Backfilled: 2024-25, 2025-26 (old rules) and 2026-27. Past scores for 2022-23 .. 2025-26 are in `archive/history/scores_2023-26.csv`.

`python log_daily.py` logs today's odds/injuries plus the last 5 days of games; `python log_daily.py START END` backfills games.

## Analyses
- `elo_eras.py` - ideas 2 and 5: last-25-game results vs a frozen Elo expectation by standings rank, by lottery era; bottom-6 head-to-head closeness.
- `lineups_rest.py` - ideas 3 and 4: top-5 regulars' share of the last 5 minutes of close games; regulars sitting, by reason; by standings zone.
- `development.py` - does development time get pushed into decided games? Young (<=23) share of floor time and net points per 48 by win-probability state; how much of each loss is added after the game is decided; regression of decided-loss bleed on both teams' floor composition.
