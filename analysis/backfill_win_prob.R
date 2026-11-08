# One-off (2026-11-08): recompute Chance to Win and likely ranges in standings_history.csv for every saved day,
# using the current simulation in index.qmd. Each day uses only that day's team snapshot and the team history
# up to that day (team_projection_history.csv), with the same date seed the page uses.
# Usage: Rscript analysis/backfill_win_prob.R [--write]
suppressMessages({library(dplyr); library(tidyr); library(tibble)})
write_out <- "--write" %in% commandArgs(TRUE)
L <- readLines("index.qmd")
grab <- function(from, to) { a <- grep(from, L, fixed = TRUE)[1]; b <- grep(to, L, fixed = TRUE); b <- b[b > a][1]; L[a:(b - 1)] }
eval(parse(text = grab("draft_data <- tribble(", "draft_complete <-")))
eval(parse(text = L[grep("^(PLAYERS|TEAMS_PER_PLAYER|SEASON_START|TALENT_SD_2526|ROSTER_RHO_2526|ROSTER_RHO_FLOOR|MODEL_VERSION|LEAGUE_WINS|N_SIMS) <-", L)]))
draft_complete <- TRUE
refit <- grab("talent_sd_now <- TALENT_SD_2526", "uncertainty <- NULL")
sim <- grab("uncertainty <- NULL", "# --- Step 6")
hist_all <- read.csv("team_projection_history.csv", stringsAsFactors = FALSE) %>% mutate(date = as.Date(date))
sh <- read.csv("standings_history.csv", stringsAsFactors = FALSE) %>% mutate(date = as.Date(date))
days <- sort(unique(sh$date[!is.na(sh$win_prob)]))
res <- list()
for (i in seq_along(days)) {
  today <- days[i]
  proj_history <- hist_all %>% filter(date <= today)
  snap <- proj_history %>% filter(date == today)
  df_final_projections <- snap %>% inner_join(draft_data %>% select(team, skins_pick), by = "team") %>%
    transmute(team, skins_pick, actual_wins = wins, actual_losses = losses,
              weighted_average = if_else(skins_pick == "W", weighted, 82 - weighted), vegas_proj_wins = vegas)
  player_scores <- tibble(player = PLAYERS)
  eval(parse(text = refit)); eval(parse(text = sim))
  chk <- df_final_projections %>% inner_join(draft_data %>% select(team, player), by = "team") %>%
    group_by(player) %>% summarise(skins_snap = sum(if_else(skins_pick == "W", actual_wins, actual_losses)), .groups = "drop")
  res[[i]] <- uncertainty %>% transmute(player, date = today, new_win = win_prob, new_lo = lo80, new_hi = hi80,
                                        new_lo50 = lo50, new_hi50 = hi50, new_tsd = talent_sd_now, new_rho = rho_now,
                                        new_rho_eff = rho_eff) %>% left_join(chk, by = "player")
}
new <- bind_rows(res)
cmp <- sh %>% inner_join(new, by = c("player", "date"))
cat("rows recomputed:", nrow(cmp), " days:", length(days), "\n")
cat("days where saved skins differ from that day's team snapshot:", sum(cmp$actual_skins != cmp$skins_snap), "rows\n")
print(cmp %>% select(date, player, old = win_prob, new = new_win) %>%
        pivot_wider(names_from = player, values_from = c(old, new)) %>% as.data.frame(), digits = 3, row.names = FALSE)
if (write_out) {
  idx <- match(paste(sh$player, sh$date), paste(new$player, new$date))
  hit <- !is.na(idx)
  sh$win_prob[hit] <- new$new_win[idx[hit]]; sh$range_lo[hit] <- new$new_lo[idx[hit]]; sh$range_hi[hit] <- new$new_hi[idx[hit]]
  sh$range_lo50[hit] <- new$new_lo50[idx[hit]]; sh$range_hi50[hit] <- new$new_hi50[idx[hit]]
  sh$model_version[hit] <- paste0(MODEL_VERSION, " (backfilled 2026-11-08)")
  sh$model_talent_sd[hit] <- new$new_tsd[idx[hit]]; sh$model_rho[hit] <- new$new_rho[idx[hit]]; sh$model_rho_in_use[hit] <- new$new_rho_eff[idx[hit]]
  write.csv(sh, "standings_history.csv", row.names = FALSE)
  cat("wrote standings_history.csv\n")
}
