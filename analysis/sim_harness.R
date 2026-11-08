suppressMessages({library(dplyr); library(tidyr); library(tibble)})
args <- commandArgs(TRUE); qmd <- args[1]; day <- if (length(args) > 1) args[2] else NA
L <- readLines(qmd)
grab <- function(from, to) { a <- grep(from, L, fixed = TRUE)[1]; b <- grep(to, L, fixed = TRUE); b <- b[b > a][1]; L[a:(b - 1)] }
eval(parse(text = grab("draft_data <- tribble(", "draft_complete <-")))
eval(parse(text = L[grep("^(TALENT_SD_2526|ROSTER_RHO_FLOOR|RHO_RAMP|N_SIMS|MODEL_VERSION|LEAGUE_WINS) <-", L)]))
PLAYERS <- c("Eristeo", "Brian", "Adam"); draft_complete <- TRUE
ph <- read.csv("team_projection_history.csv") %>% mutate(date = as.Date(date))
today <- if (is.na(day)) max(ph$date) else as.Date(day)
cur <- ph %>% filter(date == today)
df_final_projections <- cur %>% inner_join(draft_data %>% select(team, skins_pick), by = "team") %>%
  transmute(team, skins_pick, actual_wins = wins, actual_losses = losses,
            weighted_average = if_else(skins_pick == "W", weighted, 82 - weighted), vegas_proj_wins = vegas)
talent_sd_now <- TALENT_SD_2526; rho_now <- ROSTER_RHO_FLOOR
player_scores <- tibble(player = PLAYERS)
eval(parse(text = grab("uncertainty <- NULL", "# --- Step 6")))
cat(as.character(today), "games/team", round(g_now, 1), "rho_eff", round(rho_eff, 3), "\n")
print(uncertainty %>% mutate(across(where(is.numeric), ~ round(.x, 3))))
cat("league wins per sim: mean", round(mean(colSums(final_w)), 1), "sd", round(sd(colSums(final_w)), 1), "\n")
