# NBA Skins Standings Tracker

An automated NBA fantasy league tracking system that scrapes live standings and multiple projection sources to track a 6-player "skins" draft league throughout the 2024-25 season.

## 📊 Project Overview

**Skins Concept**: Players draft NBA teams and earn "skins" based on either wins (W pick) or losses (L pick). The system tracks:
- Live actual performance from ESPN standings
- Multiple projection sources (Vegas, TeamRankings, ESPN BPI, CBS Sports)
- Historical trends over time
- Season completion percentage

**Live Site**: Hosted on GitHub Pages, automatically updated 9 times daily via GitHub Actions

## 🏀 League Setup

### Players
- Eristeo
- Matt
- Brian
- Adam
- Thomas
- Kenneth

### Draft Format
- 6 players × 5 teams each = 30 NBA teams
- Snake draft (picks 1-30)
- Each team assigned either "W" (wins) or "L" (losses) as skins source

## 📁 Repository Structure

```
/
├── index.qmd                      # Main Quarto document (source)
├── index.html                     # Generated output (deployed to GitHub Pages)
├── standings_history.csv          # Player-level historical data
├── team_vegas_history.csv         # Team-level Vegas odds backfill
└── .github/workflows/publish.yml  # Automation workflow
```

## 🔄 Data Sources

### 1. ESPN Standings (Actual Results)
- **URL**: `https://www.espn.com/nba/standings`
- **Method**: HTML scraping (rvest)
- **Data**: Live wins and losses for all 30 teams
- **Frequency**: Every render (9x daily)

### 2. Rotowire Vegas Odds
- **URL**: `https://www.rotowire.com/betting/nba/tables/team-futures.php?future=Win%20Totals`
- **Method**: JSON API
- **Books**: MGM, DraftKings, Caesars, BetRivers, HardRock, FanDuel, ESPNBet
- **Processing**: 
  - Adjusts totals by ±0.5 based on over/under odds
  - Creates composite projection (mean of 7 books)
  - Converts to skins (≥41 wins → use wins, else 82 - wins)
- **Issue**: Teams sometimes missing → uses `team_vegas_history.csv` for backfill

### 3. TeamRankings Projections
- **URL**: `https://www.teamrankings.com/nba/projections/standings/`
- **Method**: HTML table scraping
- **Data**: Projected wins and losses

### 4. ESPN BPI
- **URL**: `https://www.espn.com/nba/bpi/_/view/projections`
- **Method**: HTML table scraping
- **Data**: Overall projected W-L record

### 5. CBS Sports Projections
- **URL**: `https://www.cbssports.com/nba/standings/`
- **Method**: HTML table scraping
- **Data**: 2025 season win projections
- **Processing**: Extracts from both Eastern and Western conference tables

## 📐 Key Calculations

### Actual Skins
```r
actual_skins = if_else(skins_pick == "W", actual_wins, actual_losses)
```

### Skins Percentage
```r
skins_pct = actual_skins / games_played
```
- Displayed as percentage (e.g., "76.5%")
- **Global League Average**: total_league_skins / total_league_games

### % Projected (Pace-Based)
```r
pct_projected = skins_pct × 82
```
- **Team level**: Each team's pace projection
- **Player level**: Sum of all team pct_projected values

### Weighted Average
**With Vegas data** (Vegas available):
```r
(vegas_consensus × 0.25) + (tr_skins × 0.38) + (espn_skins × 0.25) + (cbs_skins × 0.12)
```

**Without Vegas data** (Vegas missing):
```r
(tr_skins × 0.50) + (espn_skins × 0.34) + (cbs_skins × 0.16)
```

### Projection Average
```r
mean(weighted_average, vegas_consensus, team_rankings, espn_bpi, cbs_sports)
```

### Season Completion
```r
season_completion_pct = (total_games_played / 2460) × 100
```
- Total NBA season games: 30 teams × 82 games = 2,460

## 📊 Display Tables

### Table 1: Skins Standings (Player Summary)
**Columns**: player, Actual Skins, Skins %, % Projected, Weighted Average, Vegas Consensus, TeamRankings, ESPN BPI, CBS Sports, Projection_Average

**Special Row**: League Average (bottom row)
- Uses global calculations (total league skins / total league games)
- Prevents inflation from players with more games

**Formatting**:
- Actual Skins: Integer
- Skins %: Percentage with 1 decimal (e.g., "76.5%")
- All others: 1 decimal place
- League Average row: Gray background (#F0F0F0)

**Highlighting**:
- Actual Skins: Green (#E8F5E9)
- Skins %: Yellow (#FFF9C4)
- Weighted Average: Light green (#DFF0D8)

### Table 2: Standings and Projections by Player
**Structure**: 6 separate tables (one per player), seamlessly connected

**Player Order**: Eristeo, Matt, Brian, Adam, Thomas, Kenneth

**Columns**: Abbr, Skins Pick, Actual Skins, Skins %, % Projected, Weighted Average, Vegas Consensus, TeamRankings, ESPN BPI, CBS Sports, Projection Average

**Features**:
- Gray header bar with player name
- Column headers repeat for each player
- Teams sorted by Actual Skins (descending)
- Same formatting and highlighting as Table 1

### Table 3: Standings and Projections by Team
**Columns**: Team, Player, Pick Type, Actual Skins, Skins %, % Projected, Weighted Average, Vegas Consensus, TeamRankings, ESPN BPI, CBS Sports, Projection Average

**Sort**: Descending by Actual Skins

**Formatting**: Same as other tables

## 📈 Charts (9 Total)

### Colorblind-Friendly Palette
```r
Eristeo: #0077BB (Blue)
Brian: #CC3311 (Red)
Adam: #33BBEE (Cyan)
Thomas: #009988 (Teal)
Kenneth: #EE7733 (Orange)
Matt: #EE3377 (Magenta)
```

### Chart Specifications

1. **Skins Over Time**
   - Y-axis: 0 to max, integers
   - Starts one day before first games (with 0 values)

2. **Skins % Over Time**
   - Y-axis: 45% to max
   - Format: Percentage with 1 decimal

3. **% Projected Over Time**
   - Y-axis: 180 to max
   - Format: 1 decimal place

4-9. **Projection Source Charts**
   - Weighted Average
   - Vegas Consensus
   - TeamRankings
   - ESPN BPI
   - CBS Sports
   - Projection Average
   - Y-axis: 220 to max
   - Format: 1 decimal place

## 🔧 Historical Data Tracking

### Player History (standings_history.csv)
**Columns**:
- player, actual_skins, skins_pct, pct_projected
- weighted_average, vegas_consensus, team_rankings, espn_bpi, cbs_sports
- projection_average, date

**Logic**:
- Removes existing data for current date
- Appends today's data
- Adds zero starting point (day before first games)

### Team Vegas History (team_vegas_history.csv)
**Purpose**: Backfill missing Vegas odds

**Columns**: team, vegas_consensus, date

**Process**:
1. Records all 30 teams' Vegas values each run
2. When team has NA:
   - Searches history for that team
   - Finds most recent non-NA value
   - Uses historical value instead
3. Recalculates weighted_average
4. Saves updated history

**First Run Caveat**: Teams with NA stay NA (no history yet)

## ⚙️ GitHub Actions Workflow

**File**: `.github/workflows/publish.yml`

**Triggers**:
1. Push to main branch
2. Manual workflow_dispatch button
3. Scheduled (9 times daily)

**Schedule** (Central Time → UTC):
- 6:00 AM → 12:00 UTC
- 8:00 AM → 14:00 UTC
- 12:00 PM → 18:00 UTC
- 4:00 PM → 22:00 UTC
- 8:00 PM → 02:00 UTC (next day)
- 9:00 PM → 03:00 UTC
- 10:00 PM → 04:00 UTC
- 11:00 PM → 05:00 UTC
- 12:00 AM → 06:00 UTC

**Steps**:
1. Checkout repository
2. Set up R (latest version)
3. Set up Quarto
4. Install system dependencies
5. Install R packages: rmarkdown, knitr, pacman, httr, jsonlite, rvest, dplyr, tidyr, kableExtra, tibble, stringr, ggplot2, scales
6. Render Quarto document
7. **Commit both CSV files**: `git add standings_history.csv team_vegas_history.csv`
8. Push with `[skip ci]` tag
9. Deploy to GitHub Pages

## 🚀 Getting Started

### Prerequisites
- R (latest version)
- Quarto
- Git/GitHub account
- GitHub Pages enabled

### Local Development
```bash
# Render document
quarto render index.qmd

# Preview with auto-refresh
quarto preview index.qmd --no-browse
```

### Deployment
1. Push to main branch → automatic deployment
2. Or use "Actions" tab → "Run workflow" button

## 🛠️ Maintenance

### Update Draft Data
Edit `draft_data` tibble in index.qmd (around line 30)

### Modify Projection Weights
Update weighted_average formula in index.qmd (around line 282)

### Change Colors
Modify `colorblind_colors` vector in index.qmd (around line 750)

### Adjust Schedule
Edit cron expressions in .github/workflows/publish.yml

## 🔍 Troubleshooting

### "Object 'today' not found"
**Fix**: Ensure `today <- Sys.Date()` is defined before team vegas history section

### Vegas totals too low
**Fix**: Check team_vegas_history.csv is being properly committed and loaded

### Table rendering issues
**Fix**: Ensure `results='asis'` in chunk options for HTML output

### Scraping failures
**Fix**: Check tryCatch blocks have proper fallback values

## 📝 File Format Specifications

### Team Name Standardization
All sources normalized to full names:
- "LA Clippers" → "Los Angeles Clippers"
- "Golden St." → "Golden State Warriors"
- Applied to all scraped data before joining

### Number Formatting
- **Actual Skins**: Integer (no decimals)
- **Skins %**: Percentage format (e.g., "76.5%")
- **All other numbers**: 1 decimal place (e.g., "253.8")
- **Charts**: Follow same formatting on axes

## 🎯 Key Features

✅ Automated 9x daily updates  
✅ 5 independent projection sources  
✅ Historical trend tracking  
✅ Missing data backfill system  
✅ Season completion tracking  
✅ Global league averages  
✅ Colorblind-friendly visualizations  
✅ Mobile-responsive tables  
✅ Self-contained HTML output  

## 📄 License

This is a personal fantasy league tracker. Feel free to fork and adapt for your own league!

## 🤝 Contributing

This is a personal project, but suggestions for improvements are welcome via issues.

---

**Current Season**: 2024-25 NBA Season  
**Last Updated**: November 2024  
**Maintained by**: League Commissioner
