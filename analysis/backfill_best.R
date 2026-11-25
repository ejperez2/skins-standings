# One-off (2026-11-15): fill standings_history.csv's win_prob_best for every saved day, using the "Best guess" run in
# index.qmd (same projections; TALENT_SD 7.2 and roster correlation 0.15, the values 24 past seasons support).
# Same per-day setup as backfill_win_prob.R. Saved default odds (win_prob) are left as they were.
# Usage: Rscript analysis/backfill_best.R [--write]
suppressMessages({library(dplyr); library(tidyr); library(tibble)})
write_out <- "--write" %in% commandArgs(TRUE)
L <- readLines("index.qmd")
grab <- function(from, to) { a <- grep(from, L, fixed = TRUE)[1]; b <- grep(to, L, fixed = TRUE); b <- b[b > a][1]; L[a:(b - 1)] }
eval(parse(text = grab("draft_data <- tribble(", "draft_complete <-")))
eval(parse(text = L[grep("^(PLAYERS|TEAMS_PER_PLAYER|SEASON_START|TALENT_SD_2526|ROSTER_RHO_2526|ROSTER_RHO_FLOOR|TALENT_SD_HIST|ROSTER_RHO_BEST|REFIT_MAX_WEIGHT|RHO_REFIT_MAX_WEIGHT|MODEL_VERSION|LEAGUE_WINS|N_SIMS) <-", L)]))
eval(parse(text = grab("MODEL_VERSION <-", "LEAGUE_WINS <-")))
draft_complete <- TRUE
eval(parse(text = grab("talent_fade <- function(left) {", "MODEL_VERSION <-")))
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
  cat(as.character(today), "talent sd", round(talent_sd_now, 2), "/", round(talent_sd_best, 2), "| cautious", round(uncertainty$win_prob, 3), "| best guess",
      if (is.null(uncertainty_best)) "NA" else round(uncertainty_best$win_prob, 3), "\n")
  if (!is.null(uncertainty_best)) res[[length(res) + 1]] <- uncertainty_best %>% transmute(player, date = today, v = win_prob)
}
new <- bind_rows(res)
if (write_out) {
  if (!"win_prob_best" %in% names(sh)) sh$win_prob_best <- NA_real_
  idx <- match(paste(sh$player, sh$date), paste(new$player, new$date))
  sh$win_prob_best[!is.na(idx)] <- new$v[idx[!is.na(idx)]]
  write.csv(sh, "standings_history.csv", row.names = FALSE)
  cat("wrote standings_history.csv\n")
}
