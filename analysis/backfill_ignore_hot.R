# One-off (2026-11-14): fill standings_history.csv's win_prob_ignore_hot for every saved day, using the "ignore hot start"
# run in index.qmd (skins won so far kept; rest of season at each team's opening-night projected rate).
# Same per-day setup as backfill_win_prob.R. Days before any games are played stay NA (the chart falls back to win_prob).
# Re-run 2026-11-25: the view now uses the headline (Best guess) settings, so earlier days were recomputed with them.
# Days already saved by that model are left as they were. Days run in parallel (4 cores; ~2 simulations per day).
# What the page actually published stays in forecast_log.csv, which this script does not touch.
# Usage: Rscript analysis/backfill_ignore_hot.R [--write]
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
caut <- grep('  # "Cautious" (Chance to Win toggle', sim, fixed = TRUE)
caut_end <- grep("summarise(proj = sum(if_else(skins_pick == \"W\", proj_w, 82 - proj_w)), .groups = \"drop\"), by = \"player\")", sim, fixed = TRUE)
caut_end <- caut_end[caut_end > caut][1]
stopifnot(length(caut) == 1, !is.na(caut_end))
sim <- c(sim[seq_len(caut - 1)], "  uncertainty_cautious <- NULL   # not needed here", sim[(caut_end + 1):length(sim)])
hist_all <- read.csv("team_projection_history.csv", stringsAsFactors = FALSE) %>% mutate(date = as.Date(date))
sh <- read.csv("standings_history.csv", stringsAsFactors = FALSE) %>% mutate(date = as.Date(date))
done <- unique(sh$date[grepl("best guess default", sh$model_version)])   # already computed with the current settings
days <- setdiff(sort(unique(sh$date[!is.na(sh$win_prob)])), done)
days <- as.Date(days, origin = "1970-01-01")
one_day <- function(today) {
  proj_history <- hist_all %>% filter(date <= today)
  snap <- proj_history %>% filter(date == today)
  if (nrow(snap) != 30) { cat(as.character(today), "no 30-team snapshot, skipped\n"); return(NULL) }
  df_final_projections <- snap %>% inner_join(draft_data %>% select(team, skins_pick), by = "team") %>%
    transmute(team, skins_pick, actual_wins = wins, actual_losses = losses,
              weighted_average = if_else(skins_pick == "W", weighted, 82 - weighted), vegas_proj_wins = vegas)
  player_scores <- tibble(player = PLAYERS)
  remaining_games <- nba_schedule %>% filter(date_et >= today)
  eval(parse(text = refit)); eval(parse(text = sim))
  if (is.null(uncertainty_pre)) return(NULL)
  uncertainty_pre %>% transmute(player, date = today, v = win_prob)
}
res <- parallel::mclapply(days, function(d) tryCatch(one_day(d), error = function(e) conditionMessage(e)), mc.cores = 4)
bad <- vapply(res, is.character, TRUE)
if (any(bad)) stop("failed days: ", paste(days[bad], unlist(res[bad]), collapse = "; "))
new <- bind_rows(res)
old <- sh %>% select(player, date, old = win_prob_ignore_hot)
print(new %>% left_join(old, by = c("player", "date")) %>% mutate(across(c(v, old), ~ round(.x, 3))) %>%
        tidyr::pivot_wider(names_from = player, values_from = c(old, v)) %>% as.data.frame())
if (write_out) {
  if (!"win_prob_ignore_hot" %in% names(sh)) sh$win_prob_ignore_hot <- NA_real_
  idx <- match(paste(sh$player, sh$date), paste(new$player, new$date))
  sh$win_prob_ignore_hot[!is.na(idx)] <- new$v[idx[!is.na(idx)]]
  write.csv(sh, "standings_history.csv", row.names = FALSE)
  cat("wrote standings_history.csv\n")
}
