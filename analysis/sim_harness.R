# Run the page's Chance to Win code (index.qmd) on a saved day: Rscript analysis/sim_harness.R index.qmd [YYYY-MM-DD]
# Uses that day's team snapshot and every regular-season game dated that day or later (ESPN).
suppressMessages({library(dplyr); library(tidyr); library(tibble)})
args <- commandArgs(TRUE); qmd <- args[1]; day <- if (length(args) > 1) args[2] else NA
L <- readLines(qmd)
grab <- function(from, to) { a <- grep(from, L, fixed = TRUE)[1]; b <- grep(to, L, fixed = TRUE); b <- b[b > a][1]; L[a:(b - 1)] }
eval(parse(text = grab("draft_data <- tribble(", "draft_complete <-")))
eval(parse(text = L[grep("^(PLAYERS|TEAMS_PER_PLAYER|SEASON_START|TALENT_SD_2526|ROSTER_RHO_2526|ROSTER_RHO_FLOOR|MODEL_VERSION|LEAGUE_WINS|N_SIMS) <-", L)]))
draft_complete <- TRUE
fetch_block <- grab("HOME_EDGE <- 0.22", "nba_schedule <- tryCatch(")
eval(parse(text = fetch_block))
t0 <- Sys.time(); nba_schedule <- fetch_nba_schedule(); cat("schedule:", nrow(nba_schedule), "games, fetched in", round(as.numeric(Sys.time() - t0, units = "secs"), 1), "s\n")
ph <- read.csv("team_projection_history.csv") %>% mutate(date = as.Date(date))
today <- if (is.na(day)) max(ph$date) else as.Date(day)
remaining_games <- nba_schedule %>% filter(date_et >= today)
cur <- ph %>% filter(date == today)
df_final_projections <- cur %>% inner_join(draft_data %>% select(team, skins_pick), by = "team") %>%
  transmute(team, skins_pick, actual_wins = wins, actual_losses = losses,
            weighted_average = if_else(skins_pick == "W", weighted, 82 - weighted), vegas_proj_wins = vegas)
talent_sd_now <- TALENT_SD_2526; rho_now <- ROSTER_RHO_FLOOR
player_scores <- tibble(player = PLAYERS)
t0 <- Sys.time()
eval(parse(text = grab("uncertainty <- NULL", "# --- Step 6")))
cat(as.character(today), "| method:", sim_method, "|", sched_note, "| rho_eff", rho_eff, "strength rho", round(rho_strength, 3),
    "| sim time", round(as.numeric(Sys.time() - t0, units = "secs"), 1), "s\n")
print(uncertainty %>% mutate(across(where(is.numeric), ~ round(.x, 3))) %>% as.data.frame())
sp <- sim_player[PLAYERS, ]
cat("means", round(rowMeans(sp), 1), "| corr Adam-Eristeo", round(cor(sp["Adam", ], sp["Eristeo", ]), 2), "Brian-Eristeo", round(cor(sp["Brian", ], sp["Eristeo", ]), 2),
    "| league wins mean", round(mean(colSums(final_w)), 1), "sd", round(sd(colSums(final_w)), 1), "\n")
cat("team mean - proj: max", round(max(abs(rowMeans(final_w) - unc_teams$proj_w)), 2), "| team sd / intended: ", round(range(apply(final_w, 1, sd) / unc_teams$sd), 2), "\n")
gap <- rowMeans(final_w) - unc_teams$proj_w
cat("per-player sum of team gaps (sim mean - projection, skins):", round(tapply(ifelse(unc_teams$skins_pick == "W", gap, -gap), unc_teams$player, sum), 2), "\n")
