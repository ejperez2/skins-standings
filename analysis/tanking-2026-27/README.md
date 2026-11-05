# Are the new lottery rules making tanking worse? (as of Nov 5, 2026)

A test of the claim in Sporting News' *"NBA's anti-tanking rules are not having the desired effect"*
(Nov 5, 2026). It checks that claim against every regular-season game from seven earlier seasons
(2018-19 through 2025-26; 2020-21 is left out because of its December, COVID-shortened start).

**Bottom line: early-season data cannot answer the question, and what it does show does not point to more tanking.**
This season's standings really are more spread out than usual after about 8 games, mostly at the bottom.
The extra spread does not come from teams that set out to be bad:

1. The teams the betting market expected to be bad are playing exactly as badly as expected.
2. The bottom of the standings is full of teams that were expected to be average: Jazz, Hornets, Suns and Magic.
3. One sign of tanking is a weak team falling apart in the fourth quarter of a close game. That pattern is no stronger than in a normal early season.
4. In past seasons, tanking showed up after the trade deadline, and early-season results never measured it.

The real test is February–April 2027, and the 2025-26 post-deadline numbers below are the benchmark.

## What the rules changed

The "3-2-1" lottery was approved in May 2026 by a 29-1 vote and runs through 2029. Under it:

- Every non-playoff team gets one to three lottery balls.
- The three worst teams get *fewer* balls than teams 4th-10th from the bottom, but cannot fall below pick 12.
- The league office can now cut a suspected tanker's odds.

Reports on the exact percentages conflict, but in every version, finishing bottom-3 is now worse than finishing 4th-10th from the bottom.
The rules therefore give the worst teams a reason to win more, not less. If the bottom is deeper this season, the incentives are an unlikely cause.

## Method

- **Data:** every regular-season final from ESPN's scoreboard API, including quarter-by-quarter scores (`games.csv`, built by `fetch.py`).
  All-Star and other exhibition games are dropped.
- **Same point in the season:** each season is cut at its first 121 games, which is where 2026-27 stood through Nov 4 (about 8.07 games per team).
  This lines seasons up by games played, not by calendar date. It reproduces the article's 2026-27 win table exactly
  and is within one team per bucket for 2025-26.
- **Correcting for luck:** after 8 games, a lot of the gap between teams is random.
  The analysis subtracts the variance that chance alone would produce, which is about 0.25/n for win% and about 13²/n for average point margin.
  What remains is an estimate of the real difference in team quality, labelled "talent SD" below.
- **Simulation:** each earlier season's full-season team ratings are played out over this season's actual first 121 games, 2,000 times per season.
  The question is how often chance alone produces a spread as wide as this season's.
  This baseline is generous to the article, because those full-season ratings already include each year's late-season tanking.
- **Preseason expectations:** betting win totals are used for 2026-27 (Oct 20), 2024-25 (opening night), 2025-26 (about 4 games in) and 2023-24 (about 5 games in).
  Wins are converted to an expected point margin with (W − 41) / 2.7.

Run order: `python3 fetch.py games.csv`, then `python3 analyze_same_point.py games.csv out.csv`, then `python3 analyze_context.py games.csv`.
`analyze_context.py` also reads the repo's projection CSVs.

## 1. Yes, this season is unusually spread out at the 8-game mark

| after 121 games | 18-19 | 19-20 | 21-22 | 22-23 | 23-24 | 24-25 | 25-26 | **26-27** | z vs prior |
|---|---|---|---|---|---|---|---|---|---|
| SD of win% | .235 | .211 | .212 | .202 | .186 | .223 | .208 | **.244** | +2.2 |
| SD of team avg margin | 7.4 | 5.9 | 6.2 | 5.7 | 6.4 | 7.5 | 6.9 | **8.3** | +2.4 |
| Talent SD of margin (luck removed) | 6.1 | 4.1 | 4.5 | 3.8 | 4.8 | 6.2 | 5.5 | **7.1** | +2.3 |
| Teams with ≤1 win | 3 | 2 | 4 | 1 | 1 | 3 | 3 | **6** | +3.2 |
| Teams with avg margin ≤ −10 | 4 | 2 | 2 | 1 | 1 | 1 | 3 | **6** | +3.5 |
| Avg margin, bottom-5 teams | −11.9 | −9.0 | −9.9 | −7.6 | −8.7 | −9.7 | −11.4 | **−13.3** | −2.4 |
| Avg margin, top-5 teams | 10.4 | 8.7 | 10.1 | 10.0 | 9.9 | 12.5 | 9.8 | **10.6** | +0.3 |
| Share of games won by 20+ | .231 | .157 | .165 | .157 | .149 | .165 | .207 | **.231** | +1.8 |
| Share of games within 5 | .298 | .248 | .223 | .264 | .314 | .281 | .298 | **.207** | −2.2 |

The article is right on the facts. On most of these measures 2026-27 ranks 1st of 8, and the gap is at the **bottom**.
The top of the standings is normal, so the article's "more good teams" point does not hold up once you look at point margins.

These numbers need context, though:

- **The simulation p-values depend on which statistic you pick.** In the simulation, a win% spread as wide as this season's happens about 12% of the time, and a point-margin spread about 15%.
  Six teams with ≤1 win happens only about 1% of the time, but that is the one statistic the article chose after seeing the standings.
  The broad, pre-chosen measures put this season at roughly "1-in-7 unusual".
- **Spread after 8 games always shrinks.** In the seven earlier seasons, the spread of team margins at this point averaged 6.6 and finished the season at 5.1.
  Across seasons, the spread after 8 games correlates only r = 0.62 with the final spread.
- **Blowouts were already rising.** The noise in single-game margins has grown from about 12.5 points (2018-20) to about 14 (2023-26).
  Excluding games that involve this season's bottom-6 teams, the 20-point blowout rate is .187, compared with .167–.169 in 2024-26 and .11–.16 before that.
  More lopsided games is a league-wide trend that started before the new rules. Bad teams are not the only cause.
  None of the blowout differences against the pooled earlier seasons is statistically significant: Fisher p = 0.17 for 20+ point games, and Mann-Whitney p = 0.09 for absolute margin.

## 2. The bottom of the standings is not made up of teams built to be bad

Preseason win totals were **not** more spread out this year. The standard deviation was 10.3 wins, against 11.0 in 2024-25 and 10.8 in 2025-26.

Early results also track the preseason lines about as closely as in other years.
Regressing each team's early point margin on its preseason-implied margin gives a slope of 1.21 ± 0.34 this season and 1.24 ± 0.23 last season.

| season | bottom-10 by preseason line: actual minus expected margin | top-10: actual minus expected |
|---|---|---|
| 2023-24 | −0.3 | +0.4 |
| 2024-25 | −0.5 | −0.5 |
| 2025-26 | −0.4 | +0.5 |
| **2026-27** | **+0.3** | **+2.0** |

The ten teams expected to be worst are playing slightly *better* than expected this season, more so than in any of the three earlier seasons.
The deep bottom comes from teams whose preseason lines put them near the middle:

| 2026-27 | record | avg margin | preseason win total | margin vs expectation |
|---|---|---|---|---|
| CHI | 1-7 | −18.0 | 29.2 | −13.6 |
| SAC | 1-7 | −14.0 | 20.8 | −6.5 |
| MIL | 1-7 | −12.2 | 25.8 | −6.6 |
| UTAH | 1-7 | −11.2 | **37.3** | −9.9 |
| CHA | 3-6 | −11.1 | **37.9** | −10.0 |
| PHX | 1-5 | −11.0 | **39.3** | −10.4 |
| ORL | 2-5 | −9.0 | **44.0** | −10.1 |

Nobody thinks Orlando, Phoenix or Charlotte is tanking.
The extra depth at the bottom comes from a handful of expected-to-be-average teams collapsing, most of them because of injuries, plus one Bulls team that looks historically bad.
Meanwhile Brooklyn, Memphis, Washington and New Orleans, all projected near the bottom, are at or well above their lines.

## 3. Where tanking actually shows up: after the trade deadline

The same measures, split into three phases of each season:

| season | team quality SD (luck removed): first 121 / to deadline / post-deadline | bottom-5 avg margin post-deadline | 20+ pt blowout rate post-deadline |
|---|---|---|---|
| 2018-19 | 5.8 / 4.8 / 4.7 | −7.8 | .174 |
| 2021-22 | 4.1 / 4.4 / 5.8 | −10.3 | .219 |
| 2022-23 | 3.4 / 3.5 / 4.4 | −9.0 | .175 |
| 2023-24 | 4.5 / 5.4 / 6.0 | −10.0 | .202 |
| 2024-25 | 5.9 / 5.5 / 6.7 | −11.7 | .210 |
| **2025-26** | 5.2 / 5.3 / **7.6** | **−11.9** | **.285** |
| 2026-27 | 6.9 / – / – | | |

(2019-20 is left out of this table because COVID ended its post-deadline stretch in March.)

Under the old rules, the bad teams pulled away from the rest after the deadline, and 2025-26 was the most extreme case.
Opening weeks are a different setting. Comparing November 2025 with November 2026 compares two stretches in which nobody was tanking yet.
That comparison cannot show whether the new rules work. They can only be judged against the post-deadline row.

**Fourth-quarter fades.** Tanking looked like sitting healthy starters in the fourth quarter (the Jazz were fined for exactly that).
This test takes games within 8 points after three quarters and compares bottom-10 teams' fourth-quarter scoring margin against non-bottom opponents:

| season | early season | post-deadline |
|---|---|---|
| 2018-19 to 2023-24 | −2.3 to +0.3 | −1.3 to −2.9 |
| 2024-25 | −0.2 | −3.7 (close-game win% .32) |
| 2025-26 | −2.3 | **−4.2 (close-game win% .24)** |
| **2026-27** | **−1.7 ± 1.9** (win% .32) | – |

The two worst fourth-quarter fades in the data are the last two post-deadline stretches, the years tanking was at its worst.
This season's early figure sits in the normal early-season range, but the sample is small: 22 close games.

## 4. The article's "tanking 10"

Pooled record and average point margin (in brackets) for the ten teams, by phase:

| | 2025-26 first 121 games | 2025-26 game 121 to deadline | 2025-26 post-deadline (tank mode) | 2026-27 first 121 games |
|---|---|---|---|---|
| Pooled | 27-53 (−6.6) | 136-288 (−6.2) | 77-239 (**−9.7**) | 27-54 (**−5.2**) |

As a group, the ten are **better** than in their tanking stretch and slightly better than at this point last year, by 1.4 points per game.
Six have improved (WSH, MEM, NO, DAL, BKN, IND) and four have gotten worse (CHI, MIL, SAC, UTAH).
The article's own team notes explain the four that slipped with injuries, roster turnover and a new coach.
None of the four shows the fourth-quarter fade that marked last spring's tanking.

## Verdict

- **Are bad teams worse this season?** Somewhat. The bottom tail is about 2.4 standard deviations deeper than usual at this point.
  That is real but noisy: roughly a 1-in-7 result on broad measures, and early spreads regress.
- **Is that because of the new lottery rules or tanking?** There is no evidence for it.
  - The teams projected to be bad are performing at projection.
  - The new bottom-feeders are teams expected to be average.
  - Fourth-quarter fades look normal.
  - Under 3-2-1, finishing bottom-3 is penalized, so the incentive runs the other way.
- **What the article does get right:** removing the reward for tanking does not make bad rosters good.
  The hope that the bottom would rise once teams stopped trying to lose was always about February–April, not November.
- **What to watch:** the 2027 post-deadline period. Under the old rules in 2025-26, that stretch produced:
  - team quality spread (luck removed) of 7.6
  - bottom-5 average margin of −11.9
  - 28.5% of games decided by 20+ points
  - a fourth-quarter fade of −4.2 for bottom-10 teams in close games
  
  If 2027's post-deadline numbers come in well below those, the reform is working.

## Caveats

- All of 2026-27 is 121 games. Every number for this season carries wide uncertainty.
- The 2023-24 and 2025-26 "preseason" lines were captured 4–5 games into those seasons, so they already reflect a few results. That slightly flatters how well they match early results.
- Converting win totals to expected margin with 2.7 wins per point is a standard approximation, not a fit.
- The fourth-quarter test is rough. It ignores who was on the floor and treats any close game after three quarters as comparable.
- Lottery odds figures differ between reports. The direction of the incentive (bottom-3 gets fewer balls than 4th–10th) is the same in all of them.

Sources on the rules:
- [AP via WTOP](https://wtop.com/nba/2026/05/nbas-board-of-governors-passes-anti-tanking-changes-to-draft-lottery-process-ap-source-says/)
- [HoopsRumors](https://www.hoopsrumors.com/2026/05/nbas-board-of-governors-approves-3-2-1-lottery-reform-plan.html)
- [NBC explainer](https://www.nbcnewyork.com/nba/nba-draft-lottery-reform-anti-tanking-explainer-format/6506506/)
