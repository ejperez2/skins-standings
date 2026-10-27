"""Fetch Crafted NBA's latest season projections into crafted_latest.csv.

GitHub Actions runners get a Cloudflare challenge (HTTP 403) from craftednba.com, so a scheduled Claude Code
session runs this each morning and commits the file; index.qmd falls back to it when its own fetch fails.
Crafted OK'd a once-daily scrape of its public projections (email, Oct 27, 2026). One request per run.
Usage: python3 fetch_crafted.py
"""
import csv
import json
import re
import sys
import urllib.request

URL = "https://craftednba.com/api/team-projections"
OUT = "crafted_latest.csv"

# Team names keyed by abbreviation, from draft_data in index.qmd (Crafted's team_code matches abbr)
qmd = open("index.qmd", encoding="utf-8").read()
teams = {abbr: team for team, abbr in re.findall(r'^\s*"([A-Z][^"]+)",\s*[^,]+,\s*"([A-Z]{3})"', qmd, re.M)}
if len(teams) != 30:
    sys.exit(f"expected 30 teams in draft_data, found {len(teams)}")

req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
data = json.load(urllib.request.urlopen(req, timeout=30))
if not data.get("success"):
    sys.exit("API returned success = false")
run_date = data["data"]["projection"]["date_created"][:10]
rows = [(teams[t["team_code"]], float(t["average_projected_wins"]))
        for t in data["data"]["team_projections"] if t["team_code"] in teams]
if len(rows) != 30:
    sys.exit(f"expected 30 teams from Crafted, got {len(rows)}")

with open(OUT, "w", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_NONNUMERIC)
    w.writerow(["team", "crafted_proj_w", "run_date"])
    for team, wins in sorted(rows):
        w.writerow([team, wins, run_date])
print(f"wrote {OUT}: 30 teams, Crafted run {run_date}")
