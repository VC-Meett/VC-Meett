#!/usr/bin/env python3
"""Generate a contribution-calendar visualization from GitHub GraphQL data."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

LOGIN = os.environ.get("GITHUB_USER", "VC-Meett")
TOKEN = os.environ["GH_TOKEN"]
OUT = Path("assets/contribution-galaxy.svg")

query = """query($login:String!){user(login:$login){name login contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""
payload = json.dumps({"query": query, "variables": {"login": LOGIN}}).encode()
req = urllib.request.Request("https://api.github.com/graphql", data=payload, headers={
    "Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json",
    "User-Agent": "VC-Meett-contribution-galaxy"
})
with urllib.request.urlopen(req, timeout=30) as response:
    data = json.load(response)
if data.get("errors"):
    raise RuntimeError(json.dumps(data["errors"]))
user = data["data"]["user"]
if not user:
    raise RuntimeError(f"GitHub user {LOGIN!r} was not found")
calendar = user["contributionsCollection"]["contributionCalendar"]
weeks = calendar["weeks"]
total = calendar["totalContributions"]
levels = {"NONE": "#30343b", "FIRST_QUARTILE": "#526879", "SECOND_QUARTILE": "#668da5", "THIRD_QUARTILE": "#83b6d1", "FOURTH_QUARTILE": "#b6e6f6"}
# Card uses the profile's soft cyan/blue/lavender palette.
W, H = 1200, 330
left, top, cell, gap = 76, 106, 12, 5
grid_w = len(weeks) * (cell + gap) - gap
days = [d for w in weeks for d in w["contributionDays"]]
first_date = days[0]["date"] if days else ""
last_date = days[-1]["date"] if days else ""
updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">
<title id="title">Live GitHub contribution galaxy for {escape(user['login'])}</title>
<desc id="desc">{total} contributions in the current GitHub contribution calendar, from {escape(first_date)} to {escape(last_date)}. Generated {updated}.</desc>
<defs>
 <linearGradient id="pastel" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#39d7d0"/><stop offset=".48" stop-color="#8dcde9"/><stop offset="1" stop-color="#d7a7df"/></linearGradient>
 <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#78e5df"/><stop offset=".5" stop-color="#9ed5ef"/><stop offset="1" stop-color="#d7b6e8"/></linearGradient>
</defs>
<rect width="1200" height="330" rx="24" fill="url(#pastel)"/>
<rect x="18" y="18" width="1164" height="294" rx="20" fill="#17191d" stroke="#e8e4f0" stroke-opacity=".9"/>
<circle cx="46" cy="44" r="5" fill="#ff7779"/><circle cx="63" cy="44" r="5" fill="#ffd166"/><circle cx="80" cy="44" r="5" fill="#70d9a1"/>
<text x="104" y="49" fill="#aeb3bd" font-family="monospace" font-size="12">github.com/{escape(user['login'])} / activity</text>
<text x="76" y="86" fill="#f4f5f7" font-family="Arial,Helvetica,sans-serif" font-size="21" font-weight="700">CONTRIBUTION GALAXY</text>
<text x="1124" y="85" fill="#b9c0ca" text-anchor="end" font-family="monospace" font-size="12">'''+escape(f"{total:,} contributions") + '''</text>
''']
# Render actual calendar days, with color determined by GitHub's contributionLevel.
for wi, week in enumerate(weeks):
    for day in week["contributionDays"]:
        date = datetime.strptime(day["date"], "%Y-%m-%d")
        x = left + wi * (cell + gap)
        y = top + date.weekday() * (cell + gap)
        level = day["contributionLevel"]
        fill = levels.get(level, levels["NONE"])
        count = int(day["contributionCount"])
        # The dot halo is tied to actual activity, not random animation.
        if count > 0:
            parts.append(f'<rect x="{x-2}" y="{y-2}" width="{cell+4}" height="{cell+4}" rx="4" fill="{fill}" opacity=".16"/>')
        parts.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{fill}"><title>{escape(day["date"])}: {count} contribution{"s" if count != 1 else ""}</title></rect>')
parts.append(f'''<text x="76" y="273" fill="#aeb3bd" font-family="monospace" font-size="11">{escape(first_date)} — {escape(last_date)}</text>
<g transform="translate(770 267)" font-family="monospace" font-size="11" fill="#aeb3bd"><text x="0" y="0">LESS</text>''')
for i, level in enumerate(["NONE","FIRST_QUARTILE","SECOND_QUARTILE","THIRD_QUARTILE","FOURTH_QUARTILE"]):
    parts.append(f'<rect x="{815+i*19}" y="-12" width="12" height="12" rx="3" fill="{levels[level]}"/>')
parts.append(f'''<text x="1124" y="292" fill="#737b87" text-anchor="end" font-family="monospace" font-size="10">LIVE DATA · GENERATED {updated}</text>
</svg>''')
OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(parts), encoding="utf-8")
print(f"Wrote {OUT}: {total} contributions, {len(weeks)} weeks, {updated}")
