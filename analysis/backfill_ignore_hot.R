# One-off (2026-11-14): fill standings_history.csv's win_prob_ignore_hot for every saved day, using the "ignore hot start"
# run in index.qmd (skins won so far kept; rest of season at each team's opening-night projected rate).
# Same per-day setup as backfill_win_prob.R. Days before any games are played stay NA (the chart falls back to win_prob).
# Usage: Rscript analysis/backfill_ignore_hot.R [--write]
suppressMessages({library(dplyr); library(tidyr); library(tibble)})
write_out <- "--write" %in% commandArgs(TRUE)
L <- readLines("index.qmd")
grab <- function(from, to) { a <- grep(from, L, fixed = TRUE)[1]; b <- grep(to, L, fixed = TRUE); b <- b[b > a][1]; L[a:(b - 1)] }
eval(parse(text = grab("draft_data <- tribble(", "draft_complete <-")))
eval(parse(text = L[grep("^(PLAYERS|TEAMS_PER_PLAYER|SEASON_START|TALENT_SD_2526|ROSTER_RHO_2526|ROSTER_RHO_FLOOR|MODEL_VERSION|LEAGUE_WINS|N_SIMS) <-", L)]))
eval(parse(text = grab("MODEL_VERSION <-", "LEAGUE_WINS <-")))
draft_complete <- TRUE
eval(parse(text = grab("HOME_EDGE <- 0.22", "nba_schedule <- tryCatch(")))
nba_schedule <- fetch_nba_schedule() %>%
  filter(!status %in% c("STATUS_POSTPONED", "STATUS_CANCELED", "STATUS_SUSPENDED", "STATUS_FORFEIT"))
refit <- grab("talent_sd_now <- TALENT_SD_2526", "# Remaining schedule from ESPN")
sim <- grab("uncertainty <- NULL", "# --- Step 6")
hist_all <- read.csv("team_projection_history.csv", stringsAsFactors = FALSE) %>% mutate(date = as.Date(date))
sh <- read.csv("standings_history.csv", stringsAsFactors = FALSE) %>% mutate(date = as.Date(date))
days <- sort(unique(sh$date[!is.na(sh$win_prob)]))
res <- list()
for (i in seq_along(days)) {
  today <- days[i]
  proj_history <- hist_all %>% filter(date <= today)
  snap <- proj_history %>% filter(date == today)
  if (nrow(snap) != 30) { cat(as.character(today), "no 30-team snapshot, skipped\n"); next }
  df_final_projections <- snap %>% inner_join(draft_data %>% select(team, skins_pick), by = "team") %>%
    transmute(team, skins_pick, actual_wins = wins, actual_losses = losses,
              weighted_average = if_else(skins_pick == "W", weighted, 82 - weighted), vegas_proj_wins = vegas)
  player_scores <- tibble(player = PLAYERS)
  remaining_games <- nba_schedule %>% filter(date_et >= today)
  eval(parse(text = refit)); eval(parse(text = sim))
  cat(as.character(today), "now", round(uncertainty$win_prob, 3), "| ignore hot start",
      if (is.null(uncertainty_pre)) "NA" else round(uncertainty_pre$win_prob, 3), "\n")
  if (!is.null(uncertainty_pre)) res[[length(res) + 1]] <- uncertainty_pre %>% transmute(player, date = today, v = win_prob)
}
new <- bind_rows(res)
if (write_out) {
  if (!"win_prob_ignore_hot" %in% names(sh)) sh$win_prob_ignore_hot <- NA_real_
  idx <- match(paste(sh$player, sh$date), paste(new$player, new$date))
  sh$win_prob_ignore_hot[!is.na(idx)] <- new$v[idx[!is.na(idx)]]
  write.csv(sh, "standings_history.csv", row.names = FALSE)
  cat("wrote standings_history.csv\n")
}
