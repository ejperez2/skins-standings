# NBA Skins Standings Project - Complete Documentation

## Project Overview

This is an automated NBA "skins" fantasy league tracking system that scrapes live NBA standings and various projection sources to display current standings and projections for a 6-player draft league.

**Core Concept**: Players draft NBA teams and earn "skins" based on either wins (W) or losses (L). The system tracks actual performance and multiple projection sources.

## File Structure

```
/
├── index.qmd                      # Main Quarto document
├── standings_history.csv          # Player-level historical data
├── team_vegas_history.csv         # Team-level Vegas odds history
└── .github/workflows/publish.yml  # GitHub Actions workflow
```

## Players and Draft

**Players**: Eristeo, Matt, Brian, Adam, Thomas, Kenneth

**Draft Data** (hardcoded in index.qmd):
- Each player drafted 5 NBA teams
- Each team has a "skins_pick" (W or L)
- Teams drafted in order (draft_pick 1-30)

Example:
- Utah Jazz → Eristeo, L pick (earns losses)
- Oklahoma City Thunder → Matt, W pick (earns wins)

## Data Sources

### 1. **ESPN Standings** (Live Actual Data)
- URL: `https://www.espn.com/nba/standings`
- Method: HTML scraping with rvest
- Returns: Actual wins and losses for all 30 teams
- Frequency: Updates with each script run
- Error Handling: Falls back to zero wins/losses if scrape fails

### 2. **Rotowire Vegas Odds** (Win Total Projections)
- URL: `https://www.rotowire.com/betting/nba/tables/team-futures.php?future=Win%20Totals`
- Method: JSON API scraping
- Returns: Win totals from 7 sportsbooks (MGM, DraftKings, Caesars, BetRivers, HardRock, FanDuel, ESPNBet)
- **Calculation Logic**:
  - For each book: Adjusts total by ±0.5 based on over/under odds
  - Creates composite projection as mean of all 7 adjusted totals
  - Converts to "skins consensus": if projection ≥ 41, use wins; else use losses (82 - wins)
- **CRITICAL ISSUE**: Teams sometimes missing from this source → handled with historical backfill (see below)

### 3. **TeamRankings Projections**
- URL: `https://www.teamrankings.com/nba/projections/standings/`
- Method: HTML table scraping
- Returns: Projected wins and losses
- Skins calculation: Use wins if >41, else use losses

### 4. **ESPN BPI Projections**
- URL: `https://www.espn.com/nba/bpi/_/view/projections`
- Method: HTML table scraping
- Returns: Projected overall W-L record
- Skins calculation: Use wins if >41, else use losses

## Key Calculations

### Actual Skins
```r
actual_skins = if_else(skins_pick == "W", actual_wins, actual_losses)
```

### Games Played
```r
games_played = actual_wins + actual_losses
```

### Skins %
```r
skins_pct = if_else(games_played > 0, actual_skins / games_played, 0)
```
- Displayed as percentage with 1 decimal (e.g., "76.5%")

### % Projected
```r
pct_projected = skins_pct * 82
```
- Team level: Each team's pace-based projection
- Player level: **SUM of all team pct_projected values** (NOT player's overall skins_pct × 82)

### Weighted Average
```r
# If Vegas data available:
weighted_average = (vegas_consensus * 0.31) + (tr_skins * 0.10) + (espn_skins * 0.59)

# If Vegas data missing:
weighted_average = (tr_skins * 0.25) + (espn_skins * 0.75)
```

### Projection Average
```r
projection_average = mean(weighted_average, vegas_consensus, team_rankings, espn_bpi)
```

## Historical Data Tracking

### Player History (standings_history.csv)
**Columns**:
- player
- actual_skins
- skins_pct
- pct_projected
- weighted_average
- vegas_consensus
- team_rankings
- espn_bpi
- projection_average
- date

**Update Logic**:
- Removes any existing data for current date
- Appends current day's data
- Adds zero starting point on day before first games

### Team Vegas History (team_vegas_history.csv)
**Purpose**: Handle missing teams in Vegas odds scraping

**Columns**:
- team
- vegas_consensus
- date

**Update Logic**:
1. Records all 30 teams' Vegas consensus values each run
2. When a team has NA for Vegas odds:
   - Searches team_vegas_history for that team
   - Finds most recent non-NA value (date < today)
   - Uses that historical value instead of NA
3. Recalculates weighted_average with filled-in value
4. Saves updated history

**First Run Behavior**: 
- Creates file with today's data
- Teams with NA remain NA (no history to pull from)
- Future runs can backfill using this data

## Team Name Standardization

**Critical Function**: `standardize_team_names()`
- All data sources use different team name formats
- Function normalizes to full names (e.g., "LA Clippers" → "Los Angeles Clippers")
- Applied to all scraped data before joining

**All 30 Teams** (standardized format):
Atlanta Hawks, Boston Celtics, Brooklyn Nets, Charlotte Hornets, Chicago Bulls, Cleveland Cavaliers, Dallas Mavericks, Denver Nuggets, Detroit Pistons, Golden State Warriors, Houston Rockets, Indiana Pacers, Los Angeles Clippers, Los Angeles Lakers, Memphis Grizzlies, Miami Heat, Milwaukee Bucks, Minnesota Timberwolves, New Orleans Pelicans, New York Knicks, Oklahoma City Thunder, Orlando Magic, Philadelphia 76ers, Phoenix Suns, Portland Trail Blazers, Sacramento Kings, San Antonio Spurs, Toronto Raptors, Utah Jazz, Washington Wizards

## Display Tables

### Table 1: Skins Standings (Player Summary)
**Columns**: player, Actual Skins, Skins %, % Projected, Weighted Average, Vegas Consensus, TeamRankings, ESPN BPI, Projection_Average

**Formatting**:
- Actual Skins: Integer (no decimals)
- Skins %: Percentage with 1 decimal (e.g., "76.5%")
- All others: 1 decimal place

**Highlighting**:
- Actual Skins: Green background (#E8F5E9)
- Skins %: Yellow background (#FFF9C4)
- Weighted Average: Light green background (#DFF0D8)

**Sort**: Descending by Actual Skins

**Caption**: None (removed)

### Table 2: Standings and Projections by Player
**Structure**: 6 separate tables (one per player) that touch seamlessly

**Player Order**: Eristeo, Matt, Brian, Adam, Thomas, Kenneth

**Each Table Has**:
- Gray header bar with player name centered
- Column headers: Abbr, Skins Pick, Actual Skins, Skins %, % Projected, Weighted Average, Vegas Consensus, TeamRankings, ESPN BPI
- Data rows sorted by Actual Skins descending

**Formatting**: Same as Table 1

**Highlighting**: Same column highlights as Table 1

**Caption**: None

### Table 3: Standings and Projections by Team
**Columns**: Team, Player, Pick Type, Actual Skins, Skins %, % Projected, Weighted Average, Vegas Consensus, TeamRankings, ESPN BPI

**Sort**: Descending by Actual Skins

**Formatting**: Same as Table 1

**Highlighting**: Same as Table 1

**Caption**: None

## Charts

### Chart Colors (Colorblind-Friendly)
```r
colorblind_colors <- c(
  "Eristeo" = "#0077BB",   # Blue
  "Brian" = "#CC3311",     # Red
  "Adam" = "#33BBEE",      # Cyan
  "Thomas" = "#009988",    # Teal
  "Kenneth" = "#EE7733",   # Orange
  "Matt" = "#EE3377"       # Magenta
)
```

### Chart 1: Skins Over Time
- Y-axis: Actual skins (integer)
- Y-axis limits: [0, NA]
- Data: Starts one day before first games (with 0 values)

### Chart 2: Skins % Over Time
- Y-axis: Skins percentage
- Y-axis limits: **[0.45, NA]** (45% to max)
- Y-axis format: Percentage with 1 decimal (e.g., "76.5%")
- Data: Filters out zero values

### Chart 3: % Projected Over Time
- Y-axis: Projected skins
- Y-axis limits: **[180, NA]**
- Y-axis format: 1 decimal place
- Data: Filters out zero values

### Charts 4-8: Projection Sources Over Time
- Weighted Average Projection
- Vegas Consensus Projection
- TeamRankings Projection
- ESPN BPI Projection
- Projection Average

**Common Settings**:
- Y-axis limits: [220, NA]
- Y-axis format: 1 decimal place
- Data: Filters out NA values

## GitHub Actions Workflow

**File**: `.github/workflows/publish.yml`

**Triggers**:
1. Push to main branch
2. Manual workflow_dispatch
3. Schedule (9 times daily in Central Time)

**Cron Schedule** (UTC):
- 12:00 (6am CT)
- 14:00 (8am CT)
- 18:00 (Noon CT)
- 22:00 (4pm CT)
- 02:00 (8pm CT)
- 03:00 (9pm CT)
- 04:00 (10pm CT)
- 05:00 (11pm CT)
- 06:00 (Midnight CT)

**Steps**:
1. Checkout repo
2. Set up R (latest)
3. Set up Quarto
4. Install Linux system dependencies
5. Install R packages
6. Render Quarto document (index.qmd)
7. **Commit history files**: `git add standings_history.csv team_vegas_history.csv`
8. Push to main with [skip ci] tag
9. Deploy to GitHub Pages

**Critical**: Both CSV files must be committed or historical data is lost!

## Important Edge Cases & Nuances

### Missing Vegas Data
- **Problem**: Rotowire sometimes excludes teams from their API response
- **Solution**: Use team_vegas_history.csv to backfill with last known value
- **First Run**: Teams with NA stay NA (no history yet)
- **Subsequent Runs**: NA teams get most recent valid value from history

### First Day of Season
- Historical charts need zero starting point
- Code adds one row per player with date = (first_game_date - 1) and actual_skins = 0
- Only added once, not repeatedly

### Team Name Variations
- ESPN: May use "CLE" or "CLECleveland Cavaliers" format
- Rotowire: Uses full names
- TeamRankings: May abbreviate differently
- **Must standardize all before joining**

### Date Handling
- Uses system date: `Sys.Date()`
- Date must be defined BEFORE team vegas history section
- All dates stored as Date type, not character

### Number Formatting Rules
- **Actual Skins**: Integer only, no decimals
- **Skins %**: Percentage format (e.g., "76.5%")
- **All other numbers**: 1 decimal place (e.g., "253.8")
- **Charts**: Follow same formatting rules on axes

### Player Order Consistency
Must always be: Eristeo, Matt, Brian, Adam, Thomas, Kenneth
- Used in table grouping
- Used in chart legends
- Ensures consistent appearance

### Table Styling
- Header row: White text on dark blue (#0073C2) or dark gray (#444444)
- Player name bars: White text on gray (#666)
- Striped rows for readability
- Hover effects enabled
- Condensed spacing

## Common Issues & Solutions

### Issue: "Object 'today' not found"
**Cause**: Variable used before definition
**Solution**: Define `today <- Sys.Date()` immediately after df_final_projections creation

### Issue: Vegas totals too low for some players
**Cause**: NAs in Vegas data treated as zero when summing
**Solution**: Historical backfill system fills NAs before player aggregation

### Issue: % Projected wrong in player table
**Cause**: Calculated as player's skins_pct × 82 instead of sum of teams
**Solution**: `sum(pct_projected, na.rm = TRUE)` in player_scores calculation

### Issue: Table rendering breaks
**Cause**: Using complex HTML generation in loops
**Solution**: Use `results='asis'` in chunk options and cat() for HTML output

### Issue: Scraping failures
**Cause**: Website structure changes, network issues
**Solution**: tryCatch blocks with fallback data (zeros or last known values)

## R Packages Required

**In workflow**:
- rmarkdown
- knitr
- pacman
- httr
- jsonlite
- rvest
- dplyr
- tidyr
- kableExtra
- tibble
- stringr
- ggplot2
- scales

## Technical Stack

- **Language**: R
- **Document Format**: Quarto (.qmd)
- **Output**: Self-contained HTML
- **Hosting**: GitHub Pages
- **Automation**: GitHub Actions
- **Tables**: kableExtra
- **Plotting**: ggplot2
- **Web Scraping**: rvest, httr, jsonlite

## Future Considerations

### Potential Enhancements
1. Add error notifications if scraping fails
2. Show team logos in tables
3. Add "Games Back" calculations
4. Track weekly/monthly leaders
5. Add playoff projection scenarios
6. Email/Slack notifications for updates

### Known Limitations
1. Vegas odds may be missing for multiple days (builds history slowly)
2. No authentication for scraping (sites could block)
3. Network dependency (fails if sites are down)
4. No data validation (assumes scrapes are accurate)
5. Manual draft data entry required at season start

## Testing & Verification

### Before Committing Changes
1. Test render locally: `quarto render index.qmd`
2. Check both CSV files update correctly
3. Verify all player totals sum correctly
4. Inspect table formatting in browser
5. Check chart axis ranges and labels
6. Confirm historical data appends (doesn't overwrite)

### After Deployment
1. Check GitHub Actions run succeeds
2. Verify GitHub Pages updates
3. Confirm CSV files committed to repo
4. Spot-check a few player totals manually
5. Verify charts render on mobile

## Quick Reference Commands

**Local rendering**:
```bash
quarto render index.qmd
quarto preview index.qmd --no-browser
```

**Git operations** (for CSV files):
```bash
git add standings_history.csv team_vegas_history.csv
git commit -m "Update standings history [skip ci]"
git push
```

## Contact & Maintenance

**Updating Draft Data**: Edit the `draft_data` tibble in index.qmd (around line 30)

**Changing Projection Weights**: Modify weighted_average formula (around line 282)

**Adjusting Schedule**: Edit cron expressions in publish.yml

**Modifying Colors**: Update `colorblind_colors` vector (around line 750)

---

**Document Version**: 1.0
**Last Updated**: 2025-10-31
**Project Status**: Active, fully functional with historical tracking
