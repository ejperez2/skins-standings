# NBA Skins Standings Tracker - Comprehensive Documentation

An automated NBA fantasy league tracking system that scrapes live standings and multiple projection sources to track a 3-player "skins" draft league throughout the 2026-27 season.

## 📊 Table of Contents

- [Project Overview](#project-overview)
- [League Setup](#league-setup)
- [Repository Structure](#repository-structure)
- [Data Sources](#data-sources)
- [Key Calculations](#key-calculations)
- [Display Tables and Charts](#display-tables-and-charts)
- [Automation System](#automation-system)
- [Technical Architecture](#technical-architecture)
- [Troubleshooting Guide](#troubleshooting-guide)
- [Common Issues and Solutions](#common-issues-and-solutions)
- [Maintenance](#maintenance)
- [Development Tips](#development-tips)

---

## 📊 Project Overview

### Skins Concept
Players draft NBA teams and earn "skins" based on either wins (W pick) or losses (L pick). The system:
- Tracks live actual performance from ESPN standings
- Aggregates 6 projection sources (Vegas, TeamRankings, ESPN BPI, CBS Sports, Basketball Reference, and a weighted average)
- Maintains historical trends over time
- Calculates season completion percentage
- Automatically updates 9 times daily via GitHub Actions

### Core Features
- ✅ **Real-time scraping** from 6 independent sources
- ✅ **Historical backfill** for missing data (especially Vegas odds)
- ✅ **Automated deployment** via GitHub Actions
- ✅ **Self-contained HTML** output for easy viewing
- ✅ **Colorblind-friendly** visualizations
- ✅ **Mobile-responsive** tables
- ✅ **Max Projection** tracking for best-case scenarios
- ✅ **Optimized weighted average** using last season's most accurate November weightings

**Live Site**: Automatically deployed to GitHub Pages

---

## 🏀 League Setup

### Players (2026-27)
1. Eristeo
2. Brian
3. Adam

Players are configured once in `PLAYERS` at the top of `index.qmd`; player order, the league-average divisor
and per-player tables all derive from it. (2023-24 through 2025-26 were a 6-player league with 5 teams each;
that data is archived in `archive/2025-26/`.)

### Draft Format
- **Draft Date**: Sunday, October 18, 2026 (season opens Tuesday, October 20, 2026)
- **Total Teams**: 30 NBA teams (3 players × 10 teams each)
- **Draft Type**: Snake draft
- **Pick Range**: Picks 1-30
- **Skins Assignment**: Each team is assigned either "W" (wins) or "L" (losses) as the skins source

### Update Schedule (2026-27, Central time)
Every 4 hours at 6 AM, 10 AM, 2 PM and 6 PM, then hourly 8 PM - 2 AM, plus every push to `main`.
GitHub schedules run on UTC, so `publish.yml` has one cron line for CDT and one for CST; a small `gate`
job lets through only the line that matches Chicago's current offset.

### Vegas Consensus
Uses every sportsbook in Rotowire's win-totals feed (any `<book>_line` column). Each line is nudged 0.5 win
toward the side its odds favor, then averaged across the books that have a line for that team. Books that go
silent are skipped; if none have lines, Vegas is marked unavailable.

### Projection Accuracy
Once a day (first run at/after 5 AM Central) the page saves every source's projected wins for every team, plus
each team's record, to `team_projection_history.csv`. The Projection Accuracy section grades each source only
on games played *after* a saved projection: expected wins since then = (projected wins - wins at the time) /
games left x games played since, compared with actual wins since. It shows the average miss (wins per team)
since opening night and over the last 30 days, a .500 baseline, the TR/ESPN/CBS weights (5% steps) that would
have missed least, and a rolling 30-day trend chart. A window is graded once teams average 12+ games in it
(about mid-November). Weights live in `WEIGHTS` near the top of `index.qmd`. Opta, DARKO and Dunks & Threes (added Oct 21, 2026,
after opening night) are graded "since opening" from their first saved snapshot and marked with `*`.

### Chance to Win and Likely Range
Each team's final wins are simulated (10,000 seasons) around its weighted-average projection with a miss
made of two parts, fit on 2025-26 team projections vs final records:
- luck in the games left: `left * p * (1 - p)`
- the projection misjudging the team: `TALENT_SD * (left / 82)^1.5` (8.6 wins preseason in 2025-26)

Together they reproduce last season's typical miss at every stage (9.7 wins preseason, 6.2 with ~57 games
left, 3.1 with ~27 left). Player totals are summed from their teams in each simulated season. The Chance to
Win cards show each player's odds with the 50% and 80% likely ranges on a shared scale. Once teams
average 12+ games since opening night, `TALENT_SD` is re-estimated from this season's own misses
(`team_projection_history.csv`) and blended in, reaching 100% this season's data by midseason.

Teams on the same roster can miss together. Checked against 2025-26 final records, team-level ranges were
well calibrated all season, but player-level 80% ranges held only ~50-60% of outcomes from ~20 games on:
a roster's skins misses were correlated about 0.30 (`ROSTER_RHO_2526`), far more than random 5-team
groupings of the same teams (1-4% of shuffles). The simulation adds a shared draw per player, signed by
pick so W and L teams lean the same way in skins, with correlation `ROSTER_RHO_START` = 0.15 (half of
last season's, as it is one season of 6 rosters) phased in from 10 to 25 league games played (`RHO_RAMP`).
With 10-team rosters that widens mid-season player ranges about 1.5x. Once teams have played 12+ games
since the first snapshot with 20+ games, the correlation is re-estimated from this season's rosters and
blended in, capped at 50% weight (only 3 rosters). Simulations
are seeded by date so every run on a given day shows the same numbers. `win_prob`, `range_lo` and
`range_hi` are saved to `standings_history.csv`.

The first Season Charts show each player's weighted average with its 80% likely range by day, and Chance to
Win over time, both from `standings_history.csv`. (An earlier version also drew a forward-looking cone of how
the range would narrow if projections held; it was removed because flat lines with a closing cone read as a
prediction of the final order.)

### Pre-Draft Mode
`draft_data` ships with all 30 teams but blank `player`, `skins_pick` and `draft_pick` values. Until every team
has a player and a W/L pick, the page renders a **Draft Board** instead of the standings: projected wins from
every source, the average, the better side (W if avg ≥ 41, else L) and that side's projected skins, plus who
drafted each team so far. In this mode `standings_history.csv` is not written; `team_vegas_history.csv`
(team-level, pick-independent) still is. Once all 30 picks are entered, the full dashboard turns on automatically.

### Critical: Hardcoded W/L Picks
The W/L pick for each team is **hardcoded** in the `draft_data` tibble and stored in `HARDCODED_PICKS`. This prevents any logic from inferring picks based on projections (which would be circular logic). The system verifies picks match the draft on every run.

---

## 📁 Repository Structure

```
/
├── index.qmd                      # Main Quarto document (source code)
├── index.html                     # Generated output (deployed to GitHub Pages)
├── standings_history.csv          # Player-level historical data (time series)
├── team_vegas_history.csv         # Team-level Vegas odds backfill data
├── .github/
│   └── workflows/
│       └── publish.yml            # GitHub Actions automation workflow
├── README.md                      # This comprehensive documentation
└── [diagnostic files]             # Optional: For troubleshooting
```

### Key Files Explained

#### index.qmd
- **Single-chunk design**: One massive R code chunk handles everything (scraping, processing, calculations, tables, charts)
- **cache=FALSE**: Ensures fresh data on every render
- **Self-contained HTML**: Output includes all CSS/JS inline for portability

#### standings_history.csv
- **Purpose**: Time series data for charts
- **Columns**: player, actual_skins, skins_pct, pct_projected, weighted_average, vegas_consensus, team_rankings, espn_bpi, cbs_sports, basketball_reference, projection_average, max_projection, date
- **Updates**: Once per day (removes existing data for current date before appending)
- **Special**: Includes zero starting point (day before first games) for clean chart visualization

#### team_vegas_history.csv
- **Purpose**: Backfill missing Vegas odds for specific teams
- **Why needed**: Rotowire sometimes excludes teams from their API (especially MIL and SAC)
- **Columns**: team, vegas_proj_wins, date
- **Logic**: Stores projected WINS (not skins), then applies W/L picks later
- **Critical**: Only stores non-NA values to avoid pollution

---

## 🔄 Data Sources

### 1. ESPN Standings (Actual Results)
- **URLs**: ESPN's JSON standings feed `https://site.api.espn.com/apis/v2/sports/basketball/nba/standings?seasontype=2`
  and the page `https://www.espn.com/nba/standings/_/seasontype/2` (both regular season only)
- **Method**: both are read every render and the one with more games played wins. ESPN's CDN once served the
  GitHub runner a stale page (0-0 records hours after games ended, with no error), and a stale copy can only be
  missing games. The Actions log prints `ESPN standings: feed N team-games, page N team-games`.
- **Data Extracted**: Live wins and losses for all 30 teams
- **Frequency**: Every render (9x daily)
- **Reliability**: ⭐⭐⭐⭐⭐ (Highly stable)
- **Parsing**: 4 tables (East teams, East stats, West teams, West stats)

**Common Issues**:
- History rows are dated by the Chicago date (runners use UTC, which used to file evening games under tomorrow)
- ESPN sometimes uses abbreviated team names in the raw HTML
- The scraper handles this with regex cleaning and standardization

### 2. Rotowire Vegas Odds
- **URL**: `https://www.rotowire.com/betting/nba/tables/team-futures.php?future=Win%20Totals`
- **Method**: JSON API
- **Books Aggregated**: MGM, DraftKings, Caesars, BetRivers, HardRock, FanDuel, ESPNBet (7 total)
- **Processing Steps**:
  1. Extract win total lines and over/under odds from each book
  2. Adjust totals by ±0.5 based on which side has better odds
  3. Calculate composite projection (mean of 7 adjusted values)
  4. Store as projected WINS (converted to skins later using W/L picks)
- **Frequency**: Every render
- **Reliability**: ⭐⭐⭐ (Sometimes missing teams)
- **Note**: Vegas is tracked separately but NOT included in weighted average formula

**Common Issues**:
- **Missing Teams**: Rotowire sometimes excludes 2-4 teams (usually MIL, SAC)
- **Solution**: Historical backfill system with hardcoded fallback values
- **Season Changes**: Odds may disappear mid-season for eliminated teams

**Vegas Backfill Logic**:
```r
1. Check current scrape
2. If NA, check team_vegas_history.csv for most recent value
3. If no history, use hardcoded fallback (MIL: 47.25, SAC: 31.5)
4. Only save non-NA values to history to prevent pollution
```

### 3. TeamRankings Projections
- **URL**: `https://www.teamrankings.com/nba/projections/standings/`
- **Method**: HTML table scraping
- **Data Extracted**: Projected wins and losses
- **Frequency**: Every render
- **Reliability**: ⭐⭐⭐⭐⭐ (Very stable and accurate)
- **Weight in Formula**: 50% (highest weight due to proven accuracy)
- **Notes**: Combines East and West conference tables

### 4. ESPN BPI (Basketball Power Index)
- **URL**: `https://www.espn.com/nba/bpi/_/view/projections`
- **Method**: HTML table scraping
- **Data Extracted**: Overall projected W-L record
- **Frequency**: Every render
- **Reliability**: ⭐⭐⭐⭐ (Very stable)
- **Weight in Formula**: 34%
- **Format**: Combined W-L string (e.g., "52-30") that must be split

### 5. CBS Sports Projections
- **URL**: `https://www.cbssports.com/nba/standings/`
- **Method**: HTML table scraping
- **Data Extracted**: 2025 season win projections (column 16)
- **Processing**: Extracts from both Eastern and Western conference tables
- **Frequency**: Every render
- **Reliability**: ⭐⭐⭐⭐ (Stable)
- **Weight in Formula**: 16%
- **Notes**: Sometimes uses abbreviated team names (e.g., "Golden St.")

### 6. Basketball Reference (BB-Ref)
- **URL**: `https://www.basketball-reference.com/friv/playoff_prob.html`
- **Method**: HTML table scraping
- **Data Extracted**: Projected wins from playoff probability tables
- **Processing**: 
  - Extracts from separate Eastern and Western conference tables
  - Removes empty rows
  - Table structure requires special handling with `make.names()`
- **Frequency**: Every render
- **Reliability**: ⭐⭐⭐⭐ (Stable)
- **Note**: Tracked separately but NOT included in weighted average formula
- **Added**: November 2024 update

### 7. Opta / The Analyst (trial, 2026-27)
- **Page**: `https://theanalyst.com/nba-predictions` (the table is a JS widget, so the page itself has no data)
- **Method**: JSON feed the widget reads:
  `https://api.performfeeds.com/basketballdata/tournamentsimulations/1mjq6w6ezkxe611ykkj8rgz7f1?tmcl=b8hmq9h3fea4isg4f04r8ebkk&_fmt=json&_rt=c`
  (outlet key and `tmcl` season id come from the widget's `index.js`; the feed returns 403 without the widget's
  `Referer: https://dataviz.theanalyst.com/`). `tmcl` is the 2026/27 season and will need updating next season.
- **Data Extracted**: projected `Wins` for all 30 teams (full team names)
- **Note**: Shown everywhere BB-Ref is (standings row, rosters, chart, Max) and graded in Projection Accuracy,
  but **NOT** in the weighted average or Source avg. Candidate for next season's blend if it grades well.
- **Columns**: `opta` in `team_projection_history.csv` (projected wins) and `standings_history.csv` (player skins)

### 8. DARKO (trial, 2026-27)
- **Page**: `https://beta.darko.app/standings` (SvelteKit; the HTML only renders one conference)
- **Method**: `https://beta.darko.app/standings/__data.json`, which holds `eastStandings` and `westStandings` in
  SvelteKit's compact format (each object/array stores indices into one flat list; `darko_resolve` decodes it).
  Projected wins = `W`.
- **Columns**: `darko` in both history CSVs. Not in the weighted average.

### 9. Dunks & Threes (trial, 2026-27)
- **Page**: `https://dunksandthrees.com/playoff-probabilities` (server-rendered)
- **Method**: the table whose header includes "Win Totals"; column 1 = team abbreviation (same as `draft_data$abbr`),
  column 3 = average projected wins.
- **Columns**: `dnt` in both history CSVs (label "D&T" on the page). Not in the weighted average.

---

## 📐 Key Calculations

### 1. Actual Skins
```r
actual_skins = if_else(skins_pick == "W", actual_wins, actual_losses)
```
- Uses the **hardcoded** W/L pick from draft_data
- Never inferred from projections

### 2. Skins Percentage
```r
skins_pct = actual_skins / games_played
```
- Displayed as percentage (e.g., "76.5%")
- Zero if no games played yet

### 3. Global League Average
```r
league_skins_pct = total_league_skins / total_league_games
```
- **Critical**: Uses sum across ALL 30 teams (not average of 6 player averages)
- Prevents inflation from players with more games played
- Displayed in gray row at bottom of player summary table

### 4. % Projected (Pace-Based Projection)
```r
pct_projected = skins_pct × 82
```
- **Team level**: Extrapolates current pace to full 82-game season
- **Player level**: Sum of all 5 team projections (not pace × 82)
- Example: If a team is 10-2 (83.3%), % Projected = 68.3 skins

### 5. Weighted Average ⭐ UPDATED (2026-27)
`WEIGHTS` near the top of `index.qmd`: **Vegas 40%, TR 20%, ESPN 20%, CBS 20%**. Sources that are missing for a
team are re-weighted away, so until CBS publishes (once the season starts) it is Vegas 50 / TR 25 / ESPN 25.

How it was chosen (2025-26 data, RMSE vs final results):

| Blend | Oct, 30 teams (wins) | Nov, 6 players (skins) |
|---|---|---|
| Old: TR 50 / ESPN 34 / CBS 16 | 9.72 | 17.06 |
| Equal V/TR/ESPN/CBS | 9.65 | 16.65 |
| **V 40 / TR 20 / ESPN 20 / CBS 20** | **9.62** | **16.63** |
| V 50 / CBS 50 (Nov grid best) | 9.58 | 16.24 |
| Vegas only | 9.58 | 16.87 |

A 5% grid search's November optimum (V 50 / CBS 50) did worse than every simple blend on held-out players
(20.1), i.e. it fit noise from only 6 players, so a simple Vegas-led blend was used instead. October team-level
data (Oct 11-25, Vegas/TR/ESPN) favored Vegas; every blend including Vegas beat the old formula in both months.
The Projection Accuracy section re-checks this on 2026-27 data as the season goes.

### 6. Projection Average
```r
projection_average = mean(weighted_average, vegas_consensus, 
                         team_rankings, espn_bpi, cbs_sports, br_ref)
```
- Simple mean of all 6 projection sources
- Treats each source equally
- Provides alternative to weighted approach

### 7. Max Projection ⭐ NEW
```r
max_projection = pmax(weighted_average, vegas_consensus, tr_skins, 
                     espn_skins, cbs_skins, br_skins, na.rm = TRUE)
```
- Takes the **highest** projection from any source for each team
- Represents the "best case scenario" if the most optimistic model is correct
- Useful for identifying potential upside
- Summed by player to show maximum possible outcome

### 8. Season Completion
```r
season_completion_pct = (total_games_played / 2460) × 100
```
- Total possible games: 30 teams × 82 games = 2,460
- Displayed at top of page below timestamp

---

## 📊 Display Tables and Charts

The page is laid out phone-first and matches the Daily Matchups page (dark `darkly` theme, the same `sk-*` CSS
tokens and nav). Every section is emitted as raw HTML from an R chunk; the styles sit in a `<style>` block at the
top of `index.qmd` and the page behaviour in a `<script>` block at the bottom. Sections, top to bottom:

1. **Header**: nav with the **"I'm" picker**, last-updated time and a season-completion progress bar. The picker
   is stored in `localStorage` under `skinsMe`, the same key Daily Matchups uses, so picking yourself on either page
   highlights you on both (your column, card, roster and teams).
2. **How it works** (folded): the rules, historical skins %, the weighted-average weights, and how chance to win
   is simulated.
3. **Standings**: one table with players across (leader first) and rows for Skins, Skins %, Skins % projection
   (skins % × 82 per team, summed), then projected final skins from each source (Weighted avg, Vegas, TR, ESPN,
   CBS, BB-Ref, Source avg, Max). Best value in each row is bold; the league-average column hides on narrow phones.
4. **Season charts**: one interactive chart (tap or hover for values) drawn in the browser from
   `standings_history.csv`, which is embedded as JSON (`#sk-data`). Tabs: **Projection** (default; a dropdown
   switches between the weighted average with its 80% range band, each source, Max and Skins % projection),
   **Race** (gap to the league average, or total skins), **Skins %** and **To win**.
5. **Chance to win**: an always-visible caveat that the model is built on one season (2025-26) of data and should
   be expected to be inaccurate, then a bar splitting the title odds, then one card per player with chance to win, projection and
   the 50% / 80% likely range on a shared scale.
6. **Rosters**: tabs for one player at a time (opens on your roster, else the leader). Each team shows skins-misses,
   skins % projection (green/red vs the weighted average) and projected skins; tap a team for every source.
7. **All 30 teams** (folded, with draft order from `draft_pick`; sortable by tapping a header) and **Projection accuracy** (folded).

Player colors are Paul Tol's vibrant hues lightened for the dark background (checked for color-blind separation
and contrast):
```r
Eristeo:  #3E97D6 (Blue)
Brian:    #E26A54 (Red)
Adam:     #22A794 (Teal)
```

---

## ⚙️ Automation System

### GitHub Actions Workflow

**File**: `.github/workflows/publish.yml`

**Triggers**:
1. **Push to main branch**: Immediate render on code changes
2. **Manual dispatch**: Button in Actions tab for on-demand renders
3. **Scheduled cron jobs**: 9 times daily at strategic times

### Schedule (Central Time → UTC)

The workflow runs at times when NBA games are likely to have updates:

| Central Time | UTC Time | Reasoning |
|--------------|----------|-----------|
| 6:00 AM | 12:00 UTC | Morning update |
| 8:00 AM | 14:00 UTC | Pre-work check |
| 12:00 PM | 18:00 UTC | Lunch update |
| 4:00 PM | 22:00 UTC | Early games starting |
| 8:00 PM | 02:00 UTC (next day) | Peak game time |
| 9:00 PM | 03:00 UTC | Mid-game update |
| 10:00 PM | 04:00 UTC | Late game update |
| 11:00 PM | 05:00 UTC | Final games |
| 12:00 AM | 06:00 UTC | Midnight wrap-up |

**Cron Syntax Notes**:
- Times are in UTC (GitHub Actions default)
- Central Time = UTC - 5 hours (CST) or UTC - 6 hours (CDT)
- Schedule accounts for CDT offset used in comments

### Workflow Steps

```yaml
1. Checkout repository (actions/checkout@v4)
2. Set up R (r-lib/actions/setup-r@v2, latest version)
3. Set up Quarto (quarto-dev/quarto-actions/setup@v2)
4. Install system dependencies (libcurl, fontconfig, freetype, etc.)
5. Install R packages (rmarkdown, knitr, pacman, httr, jsonlite, 
                       rvest, dplyr, tidyr, kableExtra, tibble, 
                       stringr, ggplot2, scales)
6. Render Quarto document (quarto render index.qmd)
7. Commit history CSVs (standings_history.csv, team_vegas_history.csv)
   - Uses [skip ci] tag to prevent infinite loops
8. Deploy to GitHub Pages (peaceiris/actions-gh-pages@v4)
```

**Key Permissions**:
```yaml
permissions:
  contents: write  # Needed for: 
                   # 1. Pushing to gh-pages branch
                   # 2. Committing history CSV updates
```

**Important**: The workflow commits BOTH CSV files back to main branch to preserve historical data across renders.

---

## 🏗️ Technical Architecture

### Data Flow Diagram

```
1. SCRAPE (6 sources + ESPN standings)
   ↓
2. STANDARDIZE (team names across all sources)
   ↓
3. VEGAS BACKFILL (handle missing Rotowire data)
   ↓
4. CREATE all_teams (ensure all 30 teams present)
   ↓
5. JOIN (combine all sources + hardcoded W/L picks)
   ↓
6. CALCULATE (apply W/L picks to get skins for each source)
   ↓
7. WEIGHTED AVERAGE (50% TR + 34% ESPN + 16% CBS)
   ↓
8. MAX PROJECTION (best-case scenario from all sources)
   ↓
9. AGGREGATE (sum by player)
   ↓
10. HISTORICAL TRACKING (append to CSV files)
   ↓
11. GENERATE TABLES & CHARTS
   ↓
12. OUTPUT (self-contained HTML)
```

### Critical Design Decisions

#### 1. Single-Chunk Architecture
**Why**: Ensures all variables are in scope for debugging
- **Pros**: Easy to trace data flow, simple debugging
- **Cons**: Large chunk can be slow to render
- **Alternative considered**: Separate chunks with caching (rejected due to stale data risk)

#### 2. Hardcoded W/L Picks (HARDCODED_PICKS)
**Why**: Prevent circular logic where projections influence pick assignment
- Created once from draft_data
- Joined LAST in the pipeline to overwrite any vestigial code
- Verified on every run with warning if mismatch detected

#### 3. Vegas Backfill System
**Why**: Rotowire API frequently excludes 2-4 teams
- Three-tier fallback: Current scrape → Historical data → Hardcoded values
- Only saves non-NA values to prevent history pollution
- Stores projected WINS (not skins) to avoid pick-dependent storage

#### 4. Team Name Standardization
**Why**: Each source uses different naming conventions
- Centralized `standardize_team_names()` function
- Applied to ALL sources before joins
- Handles variations like:
  - "LA Clippers" vs "Los Angeles Clippers"
  - "Golden St." vs "Golden State Warriors"
  - "Okla City" vs "Oklahoma City Thunder"

#### 5. Historical Zero Starting Point
**Why**: Charts look better with a defined start
- Adds one row per player with 0 values
- Date set to day before first games (October 21, 2024)
- Only added if not already present (prevents duplicates)

#### 6. League Average Calculation
**Why**: Simple player average inflates with different game counts
```r
# CORRECT (global average):
league_avg = sum(all_team_skins) / sum(all_team_games)

# WRONG (inflated average):
league_avg = mean(player_skins_pct)  # Players with more games dominate
```

#### 7. Optimized Weighted Average Formula ⭐ NEW
**Why**: Use empirically-validated weights from previous season
- Analyzed 2023-24 November projections for accuracy
- Found 50/34/16 split (TR/ESPN/CBS) was most accurate
- Removed Vegas (betting-influenced) and BB-Ref (early-season inaccuracy)
- Footnote on dashboard explains the formula's basis

---

## 🔧 Troubleshooting Guide

### Diagnostic Workflow

If something breaks, follow this systematic approach:

#### Step 1: Identify the Symptom
- [ ] Workflow failing to run?
- [ ] Render succeeding but tables show NA?
- [ ] Specific teams missing data?
- [ ] Historical charts not updating?
- [ ] Projections seem wrong?
- [ ] Weighted average calculation incorrect?

#### Step 2: Check GitHub Actions Log
1. Go to repository → Actions tab
2. Click the failing workflow run
3. Expand each step to find errors
4. Look for:
   - R package installation failures
   - Network errors during scraping
   - Quarto rendering errors
   - CSV commit failures

#### Step 3: Test Locally
```bash
# Render locally to see full error messages
quarto render index.qmd

# Or with preview (auto-refresh)
quarto preview index.qmd --no-browse
```

#### Step 4: Create Diagnostic File
See "Common Issues" section for diagnostic QMD templates

### Log Interpretation

**Network Errors**:
```
Error in curl::curl_fetch_memory(url, handle = handle) : 
  Could not resolve host: www.rotowire.com
```
→ **Solution**: Temporary network issue or domain blocked. Check network_configuration in workflow.

**Scraping Errors**:
```
Error: Can't find column `vegas_proj_wins` in `.data`.
```
→ **Solution**: Source website changed structure. Check HTML selectors.

**Rendering Errors**:
```
Error: object 'today' not found
```
→ **Solution**: Variable defined after it's used. Check code order.

**Date/Time Errors**:
```
Error in as.Date.numeric(vegas_proj_wins) : 
  'origin' must be supplied
```
→ **Solution**: Date column not properly converted. Add `as.Date()` after reading CSV.

---

## 🚨 Common Issues and Solutions

### Issue 1: Missing Vegas Data for Specific Teams

**Symptoms**:
- Table shows "NA" for Vegas Consensus column
- Usually affects Milwaukee Bucks and/or Sacramento Kings
- Other teams show values correctly

**Root Cause**: 
Rotowire API excludes certain teams from their futures endpoint, particularly:
1. Teams with very high/low win totals that sportsbooks aren't actively taking bets on
2. Teams during certain times of season (playoffs, offseason)

**Diagnosis**:
```r
# Check if team is in raw scrape
df_vegas %>% 
  filter(grepl("Milwaukee|Sacramento", name, ignore.case = TRUE)) %>%
  nrow()
# Should return 2, but returns 0 if teams missing
```

**Solution** (already implemented in latest code):
1. **Historical backfill**: System checks `team_vegas_history.csv` for most recent value
2. **Hardcoded fallback**: If no history, uses `vegas_fallback` (empty for 2026-27; the 2025-26 MIL/SAC values were removed)
3. **Prevent pollution**: Only non-NA values saved to history

**Manual Override** (if needed):
Edit hardcoded fallback in index.qmd:
```r
vegas_fallback <- tibble(
  team = c("Milwaukee Bucks", "Sacramento Kings", "Other Team"),
  vegas_proj_wins = c(47.25, 31.5, 45.0)
)
```

### Issue 2: Historical Data Not Updating

**Symptoms**:
- Charts show old data (lines stop at previous date)
- standings_history.csv not being updated in repository

**Root Cause**:
Git commit step in workflow failing, usually due to:
1. No changes detected (`git diff --quiet` returns true)
2. Merge conflict in CSV file
3. Permissions issue

**Diagnosis**:
Check Actions log for:
```
nothing to commit, working tree clean
```

**Solutions**:

**If no changes detected**:
- This is normal if data hasn't changed
- Verify by checking if actual games have been played

**If commit failing**:
```yaml
# Check workflow has correct permissions
permissions:
  contents: write
```

**If merge conflicts**:
```bash
# Locally resolve conflicts
git pull origin main
# Manually merge standings_history.csv
git add standings_history.csv team_vegas_history.csv
git commit -m "Resolve history merge conflict"
git push
```

**Nuclear option** (destructive):
```bash
# Delete history files and let them rebuild
git rm standings_history.csv team_vegas_history.csv
git commit -m "Reset history files"
git push
```
Note: This loses ALL historical data!

### Issue 3: BB-Ref Scraping Failure

**Symptoms**:
- BB-Ref column shows NA for all teams
- Error message about Basketball Reference table structure

**Root Cause**:
Basketball Reference updates their table structure occasionally

**Diagnosis**:
Check if table structure changed:
```r
url_br <- "https://www.basketball-reference.com/friv/playoff_prob.html"
page <- read_html(url_br)
tables <- page %>% html_table()

# Check table structure
lapply(tables, names)  # Should show column names
```

**Solutions**:

**If column names changed**:
Update the column selection in index.qmd:
```r
eastern_conf_br <- tables_br[[1]]
names(eastern_conf_br) <- make.names(names(eastern_conf_br), unique = TRUE)
eastern_conf_br <- eastern_conf_br %>%
  slice(-1) %>%
  select(2, 3) %>%  # Adjust these indices if columns moved
  setNames(c("team_br", "br_proj_w"))
```

**If table indices changed**:
Basketball Reference may add/remove tables. Check:
```r
length(tables)  # Should be at least 2
```
Update `tables_br[[1]]` and `tables_br[[2]]` if needed.

**Note**: Since BB-Ref is not in the weighted average, failures here only affect the BB-Ref column and chart, not the primary projections.

### Issue 4: Team Name Mismatches

**Symptoms**:
- Specific teams show NA across all projection columns
- Same teams have data in actual standings
- Affects 1-2 teams only

**Root Cause**:
Source website changed team name format, breaking the standardization function

**Diagnosis**:
```r
# Check what names are coming from each source
df_skins %>% select(team) %>% arrange(team)  # Vegas
tr_cleaned %>% select(team) %>% arrange(team)  # TeamRankings
espn_cleaned %>% select(team) %>% arrange(team)  # ESPN BPI
# Look for naming differences
```

**Solution**:
Update `standardize_team_names()` function:
```r
standardize_team_names <- function(df, team_col) {
  df %>%
    mutate(
      !!sym(team_col) := case_when(
        grepl("New Pattern|Old Pattern", !!sym(team_col), ignore.case = TRUE) ~ "Standardized Name",
        # Add new pattern matching rules here
        TRUE ~ !!sym(team_col)
      )
    )
}
```

### Issue 5: Workflow Running Too Frequently

**Symptoms**:
- GitHub Actions shows many workflow runs
- Hitting rate limits or usage quotas

**Root Cause**:
Missing `[skip ci]` tag in commit messages, causing infinite loops

**Solution**:
Verify commit step includes skip tag:
```yaml
- name: Commit standings history
  run: |
    git config --local user.email "github-actions[bot]@users.noreply.github.com"
    git config --local user.name "github-actions[bot]"
    git add standings_history.csv team_vegas_history.csv
    git diff --quiet && git diff --staged --quiet || git commit -m "Update standings history [skip ci]"
    git push
```

The `[skip ci]` tag tells GitHub Actions to ignore this commit.

### Issue 6: Self-Contained HTML Too Large

**Symptoms**:
- index.html file size > 10 MB
- Slow to load in browser
- Git warnings about large files

**Root Cause**:
- Too many data points in charts (historical data accumulating)
- Base64-encoded images in output

**Solutions**:

**Limit historical data in charts**:
```r
# Only show last 60 days
recent_history <- history %>%
  filter(date >= today - 60)

# Use for all charts
ggplot(recent_history, ...)
```

**Reduce chart size**:
```r
# In chart code blocks, adjust dimensions
{r chart-name, fig.width=10, fig.height=5}  # Smaller than default 12x6
```

**Alternative**: Switch to non-self-contained HTML
```yaml
format: 
  html:
    self-contained: false  # Creates separate files for resources
```
Note: Requires deploying additional files to GitHub Pages.

### Issue 7: Calculations Seem Wrong

**Symptoms**:
- Weighted average doesn't match manual calculation
- Projection average wildly different from individual sources
- Skins % seems incorrect

**Diagnosis Checklist**:
- [ ] Are W/L picks applied correctly?
  ```r
  # Verify picks match draft
  HARDCODED_PICKS %>% 
    left_join(df_final_projections, by = "team") %>%
    filter(skins_pick != skins_pick_hardcoded)
  ```

- [ ] Is weighted average using correct formula (50/34/16)?
  ```r
  # Check the formula in the code
  df_final_projections %>%
    mutate(
      manual_calc = (tr_skins * 0.5) + (espn_skins * 0.34) + (cbs_skins * 0.16)
    ) %>%
    filter(abs(weighted_average - manual_calc) > 0.01)
  ```

- [ ] Are projections in WINS when they should be SKINS?
  ```r
  # All projection columns should be converted to skins:
  vegas_consensus = if_else(skins_pick == "W", vegas_proj_wins, 82 - vegas_proj_wins)
  ```

**Common Mistakes**:
1. **Forgetting to apply W/L picks**: Projections should be converted to skins
2. **Using wrong average**: Player % Projected is SUM of teams, not average
3. **League average inflation**: Must use global calculation, not mean of players
4. **Incorrect weights**: Should be 50/34/16, not old formula

### Issue 8: Charts Not Showing All Players

**Symptoms**:
- One or more players missing from time series charts
- Other players display correctly

**Root Cause**:
Historical data missing for that player, often due to:
1. Player name typo in history file
2. History file corrupted
3. Zero starting point not added for that player

**Diagnosis**:
```r
# Check history file
history <- read.csv("standings_history.csv")
unique(history$player)  # Should show all 6 players
```

**Solution**:
Manually add missing player rows to history:
```r
# Add to standings_history.csv
missing_player_rows <- tibble(
  player = "Missing Player Name",
  actual_skins = 0,
  skins_pct = 0,
  pct_projected = 0,
  weighted_average = NA,
  vegas_consensus = NA,
  team_rankings = NA,
  espn_bpi = NA,
  cbs_sports = NA,
  basketball_reference = NA,
  projection_average = NA,
  max_projection = NA,
  date = as.Date("2024-10-21")  # Day before first games
)
```

### Issue 9: Max Projection Column Missing ⭐ NEW

**Symptoms**:
- Historical data loaded but max_projection shows as NA
- Charts for max projection fail to render
- Old history file without max_projection column

**Root Cause**:
Updating from v2.1.0 to v2.2.0 without max_projection column in historical data

**Solution** (already implemented in code):
```r
# Code automatically adds column if missing
if(!"max_projection" %in% names(history)) {
  history$max_projection <- NA
}
```

If issues persist, manually add column to standings_history.csv or delete file to rebuild.

---

## 🛠️ Maintenance

### Regular Tasks

#### Weekly
- [ ] Verify all 9 scheduled runs executed successfully
- [ ] Spot-check tables for obvious errors (NA values, wrong sums)
- [ ] Monitor workflow run time (should be < 5 minutes)
- [ ] Verify weighted average formula is producing expected results

#### Monthly
- [ ] Review and clean up old workflow runs (optional)
- [ ] Check that historical CSV files are growing appropriately
- [ ] Verify all projection sources still working
- [ ] Compare weighted average accuracy to individual sources

#### Season Changes
- [ ] Update draft_data for new season
- [ ] Reset historical CSV files
- [ ] Update cron schedule if needed for playoff times
- [ ] Archive previous season's data
- [ ] Re-evaluate weighted average formula based on past season's accuracy

### Updating Draft Data

When the draft changes (new season, different teams, etc.):

1. **Update draft_data tibble** in index.qmd (around line 30):
```r
draft_data <- tribble(
  ~team, ~player, ~abbr, ~skins_pick, ~draft_pick,
  "Team Name", "Player Name", "ABR", "W", 1,
  # ... 30 rows total
)
```

2. **Verify HARDCODED_PICKS creation** (happens automatically from draft_data)

3. **Update colorblind_colors** if player names changed (near the top of `index.qmd`):
```r
colorblind_colors <- c(
  "Player1" = "#3E97D6",
  "Player2" = "#E26A54",
  # ...
)
```

4. **Archive historical files** (recommended for new season):
```bash
mkdir -p archive/<season> && git mv standings_history.csv team_vegas_history.csv archive/<season>/
```

5. **Update all_teams** if league expands/contracts:
```r
all_teams <- tibble(
  team = c("30 team names here")
)
```

### Modifying Projection Weights

To adjust the weighted average formula:

1. **Find weighted_average calculation** in index.qmd (around line 390):
```r
weighted_average = (tr_skins × 0.50) + (espn_skins × 0.34) + (cbs_skins × 0.16)
```

2. **Ensure weights sum to 1.0**:
```r
# Current: 0.50 + 0.34 + 0.16 = 1.0
```

3. **Update footnote** explaining the formula (around line 540):
```r
cat("<p style='font-size: 13px;'>November Weighted Avg: TR XX%, ESPN XX%, CBS XX% (Explanation)</p>")
```

4. **Test locally** before pushing

5. **Document reasoning** in README and commit message

**Historical Formulas for Reference**:
- v2.1.0: 20% Vegas, 30% TR, 20% ESPN, 10% CBS, 20% BB-Ref (with/without Vegas fallback)
- v2.2.0: 50% TR, 34% ESPN, 16% CBS (optimized for November based on 2023-24 data)

### Changing Update Schedule

To modify when the workflow runs:

1. **Edit .github/workflows/publish.yml**

2. **Update cron expressions**:
```yaml
- cron: '0 12 * * *'  # 6am Central (12:00 UTC)
```

Format: `minute hour day month weekday`
- Use [Crontab Guru](https://crontab.guru/) for help
- Remember UTC conversion (Central + 6 hours for CDT)

3. **Common schedules**:
```yaml
- cron: '0 */2 * * *'     # Every 2 hours
- cron: '0 0 * * *'       # Daily at midnight UTC
- cron: '0 0 * * 1'       # Weekly on Monday
- cron: '0 1,13 * * *'    # Twice daily (1am, 1pm UTC)
```

4. **Testing**: Use manual dispatch button to test changes

### Adding New Projection Sources

To add a 7th projection source:

1. **Add scraping code** after existing sources:
```r
# G: Scrape New Source
url_new <- "https://example.com/projections"
webpage_new <- read_html(url_new)
new_proj <- webpage_new %>% html_table() %>% .[[1]]
new_cleaned <- new_proj %>%
  select(team_new = 1, new_proj_w = 2) %>%
  mutate(new_proj_w = as.numeric(new_proj_w))
```

2. **Standardize team names**:
```r
new_proj <- new_proj %>% standardize_team_names("team")
```

3. **Add to df_final_projections join**:
```r
df_final_projections <- all_teams %>%
  # ... existing joins
  left_join(new_proj, by = "team") %>%
```

4. **Convert to skins**:
```r
mutate(
  new_skins = if_else(skins_pick == "W", new_proj_w, 82 - new_proj_w),
```

5. **Decide if including in weighted_average**:
```r
# If including, adjust weights to sum to 1.0:
weighted_average = (tr_skins × 0.40) + (espn_skins × 0.27) + 
                   (cbs_skins × 0.13) + (new_skins × 0.20)
```

6. **Add column to all tables**:
- player_scores summarise()
- standings_table select()
- team_projections_table select()

7. **Add column to historical tracking**:
```r
current_standings <- player_scores %>%
  select(
    # ... existing columns
    new_source = `New Source`,
```

8. **Create chart** for new source (copy existing chart and modify)

9. **Update README** with new source details and rationale for weight

---

## 💻 Development Tips

### Local Development Setup

1. **Install R** (latest version from CRAN)

2. **Install Quarto** (https://quarto.org/docs/get-started/)

3. **Install R packages**:
```r
install.packages(c('rmarkdown', 'knitr', 'pacman', 'httr', 'jsonlite', 
                   'rvest', 'dplyr', 'tidyr', 'kableExtra', 'tibble', 
                   'stringr', 'ggplot2', 'scales'))
```

4. **Clone repository**:
```bash
git clone https://github.com/yourusername/nba-skins-tracker.git
cd nba-skins-tracker
```

5. **Render document**:
```bash
quarto render index.qmd
```

6. **Preview with auto-refresh** (recommended):
```bash
quarto preview index.qmd --no-browse
```
Opens at http://localhost:4200 and auto-reloads on save

### Debugging Workflow

#### Enable Verbose Output
Add to code blocks:
```r
options(warn = 1)  # Show warnings immediately
message("Checkpoint: Loaded Vegas data")
print(summary(df_vegas))
```

#### Test Individual Sections
Comment out later sections and run just the scraping:
```r
# Test Vegas scraping only
df_vegas <- fromJSON(...) %>% as_tibble()
print(df_vegas)
# [Comment out everything after this]
```

#### Use tryCatch for Scraping
Wrap scraping in error handlers:
```r
df_vegas <- tryCatch({
  # Scraping code
}, error = function(e) {
  message("Vegas scraping failed: ", e$message)
  # Return empty tibble with correct structure
  tibble(team = character(), vegas_proj_wins = numeric())
})
```

#### Test Weighted Average Formula
Create test cases to verify calculations:
```r
# Test case
test_data <- tibble(
  tr_skins = 50,
  espn_skins = 34,
  cbs_skins = 16
)

test_data %>%
  mutate(
    weighted_avg = (tr_skins * 0.5) + (espn_skins * 0.34) + (cbs_skins * 0.16)
  )
# Should equal: 25 + 11.56 + 2.56 = 39.12
```

### Best Practices

#### Code Organization
- Keep scraping code in order: ESPN → Vegas → TeamRankings → BPI → CBS → BB-Ref
- Standardize team names immediately after scraping
- Handle missing data early (before joins)
- Apply W/L picks late (after all joins)
- Calculate weighted average after all projections converted to skins

#### Error Handling
- Use `tryCatch()` for all external API calls
- Provide fallback values for failed scrapes
- Log errors to console with `message()` or `warning()`
- Never let single source failure crash entire render

#### Performance Optimization
- Scraping is the bottleneck (network I/O)
- Consider parallel scraping for multiple sources (advanced)
- Historical CSVs grow slowly (not a concern until 1000+ rows)
- Self-contained HTML is large but acceptable (<10 MB)

#### Git Workflow
```bash
# Standard development cycle
git checkout -b feature/my-change
# Make changes to index.qmd
quarto render index.qmd  # Test locally
git add index.qmd
git commit -m "Descriptive message"
git push origin feature/my-change
# Create pull request
# After merge, workflow auto-runs
```

#### Testing Before Push
```bash
# Render locally to verify no errors
quarto render index.qmd

# Check output file exists and looks correct
open index.html  # macOS
xdg-open index.html  # Linux
start index.html  # Windows

# Verify CSV files updated (if appropriate)
git diff standings_history.csv
git diff team_vegas_history.csv

# Verify weighted average formula
# Check that 0.5 + 0.34 + 0.16 = 1.0
```

### Common Development Mistakes

1. **Forgetting to update both CSV files**
   - If you add a column to player_scores, update historical tracking too

2. **Not testing with missing data**
   - Simulate missing Vegas data by commenting out scrape
   - Verify backfill logic works

3. **Breaking team name standardization**
   - Always use standardize_team_names() function
   - Test with all 30 teams

4. **Circular logic in calculations**
   - Never use projections to determine W/L picks
   - HARDCODED_PICKS is source of truth

5. **Off-by-one errors in table indices**
   - BB-Ref tables start at index 1, not 0
   - Some sources need slice(-1) to remove header

6. **Date/timezone confusion**
   - GitHub Actions uses UTC
   - Local development may use different timezone
   - Always use `Sys.Date()` not `Sys.time()`

7. **Incorrect weight sums**
   - Weighted average weights must sum to exactly 1.0
   - Double-check: 0.50 + 0.34 + 0.16 = 1.00 ✓

---

## 📞 Support

### Quick Reference

- **Workflow not running?** → Check `.github/workflows/publish.yml` and Actions tab
- **Tables show NA?** → Check scraping errors in Actions log
- **Vegas missing for MIL/SAC?** → Historical backfill should handle this automatically
- **Charts not updating?** → Verify CSV commit step in workflow succeeded
- **Website not updating?** → Check GitHub Pages deployment in Actions
- **Code won't render locally?** → Check R package versions match workflow
- **Weighted average seems off?** → Verify 50/34/16 formula and that it equals 1.0
- **Max projection missing?** → Check if max_projection column exists in history file

### Resources

- **Quarto Documentation**: https://quarto.org/docs/
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **dplyr Reference**: https://dplyr.tidyverse.org/
- **ggplot2 Documentation**: https://ggplot2.tidyverse.org/
- **R for Data Science** (free book): https://r4ds.had.co.nz/
- **Skins Game Explanation**: https://bdubcodes.net/posts/the-nba-skins-game

### Getting Help

1. **Check this README first** (especially Troubleshooting section)
2. **Review GitHub Actions logs** for specific error messages
3. **Create diagnostic file** using provided templates
4. **Test locally** to isolate issue (workflow vs code)
5. **Check source websites** (did they change structure?)
6. **Verify formula calculations** (weighted average, max projection, etc.)

---

## 📄 License

This is a personal fantasy league tracker. Feel free to fork and adapt for your own league!

---

## 🤝 Contributing

This is a personal project, but if you find bugs or have suggestions:
1. Open an issue describing the problem
2. Include relevant diagnostic information
3. Suggest a fix if you have one

Pull requests welcome for bug fixes and enhancements!

---

## 📝 Version History

### v2.2.0 (November 2024) - Current Version ⭐
- ✅ **Optimized weighted average formula**: Changed to 50% TR, 34% ESPN, 16% CBS
  - Based on 2023-24 November projection accuracy analysis
  - Removed Vegas and BB-Ref from weighted calculation (still tracked separately)
  - Footnote explains formula basis on dashboard
- ✅ **Added Max Projection feature**: 
  - New column showing best-case scenario from all sources
  - New chart tracking max projections over time
  - Useful for identifying potential upside
- ✅ **Enhanced historical tracking**: Added max_projection column to CSV
- ✅ **Updated documentation**: Complete README overhaul reflecting current formula
- ✅ **Added Skins Game explanation**: Hyperlinked description on dashboard

### v3.0.0 (October 2026) - Three-player league
- ✅ League changed to 3 players (Eristeo, Brian, Adam) × 10 teams each; `PLAYERS` config drives everything
- ✅ Draft data reset to blanks for the October 18, 2026 draft; pre-draft Draft Board mode
- ✅ 2025-26 history archived to `archive/2025-26/`; stale Vegas fallback values removed
- ✅ Historical benchmarks shown ×2 for 10-team rosters and 2025-26 added
- ✅ Chart Y-axes auto-scale; workflow tolerates missing history files

### v2.1.0 (November 2024)
- ✅ Added Basketball Reference projections (6th source)
- ✅ Updated weighted average formula (with Vegas/BB-Ref)
- ✅ Fixed Vegas backfill issue with hardcoded fallbacks
- ✅ Prevented NA pollution in team_vegas_history.csv
- ✅ Shortened "Basketball Reference" to "BB-Ref" in tables
- ✅ Adjusted BB-Ref chart Y-axis to start at 200

### v2.0.0 (November 2024)
- ✅ Complete rewrite of Vegas backfill system
- ✅ Restructured code for better maintainability
- ✅ Enhanced historical tracking
- ✅ Improved error handling for missing data

### v1.0.0 (October 2024)
- ✅ Initial release
- ✅ 5 projection sources (Vegas, TeamRankings, ESPN, CBS)
- ✅ Automated GitHub Actions workflow
- ✅ Historical tracking and charts
- ✅ Self-contained HTML output

---

**Current Season**: 2026-27 NBA Season  
**Last Major Update**: November 2024 (v2.2.0)  
**Maintained by**: League Commissioner  
**Repository**: [Your GitHub URL Here]  
**Live Site**: [Your GitHub Pages URL Here]

---

## 🔄 What's New in v2.2.0

### Key Changes:

1. **Formula Optimization**: Weighted average now uses empirically-validated 50/34/16 split
2. **Max Projection**: Track best-case scenarios across all sources
3. **Enhanced Transparency**: Dashboard explains formula methodology
4. **Improved Documentation**: README fully updated to match current implementation

### Migration Notes:

If updating from v2.1.0:
- Historical data automatically updated with max_projection column
- Old weighted average formula deprecated
- No manual intervention required - code handles migration automatically
