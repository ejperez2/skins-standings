# Project the page's Chance to Win forward assuming every team plays exactly at its current projected pace
# and projections never change. Runs the page's own refit + simulation code from index.qmd.
suppressMessages({library(dplyr); library(tidyr); library(tibble)})
args <- commandArgs(TRUE); qmd <- args[1]; ramp_override <- if (length(args) > 1) as.numeric(strsplit(args[2], ",")[[1]]) else NULL
L <- readLines(qmd)
grab <- function(from, to) { a <- grep(from, L, fixed = TRUE)[1]; b <- grep(to, L, fixed = TRUE); b <- b[b > a][1]; L[a:(b - 1)] }
eval(parse(text = grab("draft_data <- tribble(", "draft_complete <-")))
eval(parse(text = L[grep("^(TALENT_SD_2526|ROSTER_RHO_2526|ROSTER_RHO_FLOOR|RHO_RAMP|N_SIMS|MODEL_VERSION|LEAGUE_WINS|SEASON_START) <-", L)]))
if (!is.null(ramp_override)) RHO_RAMP <- ramp_override
PLAYERS <- c("Eristeo", "Brian", "Adam"); draft_complete <- TRUE
N_SIMS <- 10000
hist0 <- read.csv("team_projection_history.csv") %>% mutate(date = as.Date(date))
d0 <- max(hist0$date); cur <- hist0 %>% filter(date == d0)
rate <- with(cur, pmin(pmax((weighted - wins) / (82 - wins - losses), 0), 1))
refit <- grab("talent_sd_now <- TALENT_SD_2526", "# Remaining schedule from ESPN")
remaining_games <- NULL   # synthetic future records do not follow the real schedule: league-total method
sim <- grab("uncertainty <- NULL", "# --- Step 6")
out <- list(); synth <- NULL
for (k in seq(0, 330, by = 3)) {
  if (exists("no_refit") && no_refit) TALENT_SD_2526 <- 8.6
  today <- d0 + k
  add <- pmin(k * 0.48, 82 - (cur$wins + cur$losses))     # ~0.48 games per team per day
  snap <- cur %>% mutate(date = today, wins = wins + add * rate, losses = losses + add * (1 - rate))
  if (k > 0) synth <- bind_rows(synth, snap)
  proj_history <- bind_rows(hist0, synth)
  df_final_projections <- snap %>% inner_join(draft_data %>% select(team, skins_pick), by = "team") %>%
    transmute(team, skins_pick, actual_wins = wins, actual_losses = losses,
              weighted_average = if_else(skins_pick == "W", weighted, 82 - weighted), vegas_proj_wins = vegas)
  player_scores <- tibble(player = PLAYERS)
  eval(parse(text = refit)); if (Sys.getenv("NOREFIT")=="1") { talent_sd_now <- 8.6; proj_history <- NULL }; eval(parse(text = sim))
  out[[length(out) + 1]] <- tibble(date = today, games = round(g_now, 1), talent_sd = round(talent_sd_now, 2),
                                   rho_eff = round(rho_eff, 3), Eristeo = uncertainty$win_prob[uncertainty$player == "Eristeo"],
                                   Adam = uncertainty$win_prob[uncertainty$player == "Adam"], Brian = uncertainty$win_prob[uncertainty$player == "Brian"])
  if (min(82 - snap$wins - snap$losses) <= 0) break
}
print(as.data.frame(bind_rows(out)), row.names = FALSE)
