#!/usr/bin/env python3
"""Generate self-contained GitHub contribution and telemetry SVGs from real GraphQL data."""
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

LOGIN = os.environ.get("GITHUB_USER", "VC-Meett")
TOKEN = os.environ["GH_TOKEN"]
ASSETS = Path("assets")

QUERY = """query($login:String!){user(login:$login){login name followers{totalCount} repositories(privacy:PUBLIC,first:1){totalCount} contributionsCollection{contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}"""

PALETTE = {
    "NONE": "#30343b",
    "FIRST_QUARTILE": "#426176",
    "SECOND_QUARTILE": "#5a849e",
    "THIRD_QUARTILE": "#83b7d2",
    "FOURTH_QUARTILE": "#c4a8e9",
}

def esc(value):
    return escape(str(value))

def fetch_profile():
    payload = json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "VC-Meett-profile-telemetry",
        },
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.load(response)
    if result.get("errors"):
        raise RuntimeError("GitHub GraphQL query failed: " + json.dumps(result["errors"]))
    user = result.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user {LOGIN!r} was not found.")
    return user

def gradient_shell(width, height, title, subtitle):
    return f'''<defs>
<linearGradient id="outer" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#39d7d0"/><stop offset=".48" stop-color="#8dcde9"/><stop offset="1" stop-color="#d7a7df"/></linearGradient>
<linearGradient id="line" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#70e2db"/><stop offset=".5" stop-color="#8dcde9"/><stop offset="1" stop-color="#c4a8e9"/></linearGradient>
</defs>
<rect width="{width}" height="{height}" rx="24" fill="url(#outer)"/>
<rect x="16" y="16" width="{width-32}" height="{height-32}" rx="20" fill="#17191d" stroke="#e5e2ed" stroke-opacity=".7"/>
<path d="M16 67H{width-16}" stroke="#333942"/>
<circle cx="43" cy="43" r="5" fill="#ff7779"/><circle cx="60" cy="43" r="5" fill="#ffd166"/><circle cx="77" cy="43" r="5" fill="#70d9a1"/>
<text x="98" y="47" fill="#9ca5b1" font-family="monospace" font-size="11">VC-MEETT / {esc(title)}</text>
<text x="48" y="101" fill="#f2f4f7" font-family="Arial,Helvetica,sans-serif" font-size="23" font-weight="700">{esc(subtitle)}</text>'''

def make_galaxy(user, updated):
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    all_days = [day for week in weeks for day in week["contributionDays"]]
    first_date = all_days[0]["date"] if all_days else ""
    last_date = all_days[-1]["date"] if all_days else ""
    active_days = sum(1 for day in all_days if int(day["contributionCount"]) > 0)
    peak = max(all_days, key=lambda day: int(day["contributionCount"]), default={"date": "—", "contributionCount": 0})
    left, top, cell, gap = 76, 151, 12, 5
    step = cell + gap
    points = {}
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            date = datetime.strptime(day["date"], "%Y-%m-%d")
            row = (date.weekday() + 1) % 7  # Sunday at top, Saturday at bottom
            points[(week_index, row)] = {
                "x": left + week_index * step + cell / 2,
                "y": top + row * step + cell / 2,
                "count": int(day["contributionCount"]),
                "level": day["contributionLevel"],
                "date": day["date"],
            }
    total_weeks_width = len(weeks) * step - gap
    parts = [f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="440" viewBox="0 0 1200 440" role="img" aria-labelledby="title desc">
<title id="title">Live contribution network for {esc(user["login"])}</title>
<desc id="desc">{total} real contributions from {esc(first_date)} to {esc(last_date)}. Each square is one calendar day and the web links connect adjacent active days. Refreshed {esc(updated)}.</desc>
{gradient_shell(1200, 440, "ACTIVITY / 12 MONTHS", "CONTRIBUTION NETWORK")}
<text x="48" y="123" fill="#9ca5b1" font-family="monospace" font-size="10">{esc(first_date)} — {esc(last_date)}</text>
<text x="965" y="99" fill="#9eddf1" text-anchor="end" font-family="monospace" font-size="10">TOTAL CONTRIBUTIONS</text>
<text x="965" y="126" fill="#f2f4f7" text-anchor="end" font-family="Arial,Helvetica,sans-serif" font-size="25" font-weight="700">{total:,}</text>
<path d="M990 84V393" stroke="#333942"/>
<text x="1017" y="105" fill="#9ca5b1" font-family="monospace" font-size="10">ACTIVE DAYS</text>
<text x="1017" y="130" fill="#f2f4f7" font-family="Arial,sans-serif" font-size="24" font-weight="700">{active_days}</text>
<text x="1017" y="172" fill="#9ca5b1" font-family="monospace" font-size="10">PEAK DAY</text>
<text x="1017" y="197" fill="#f2f4f7" font-family="Arial,sans-serif" font-size="23" font-weight="700">{int(peak["contributionCount"])}</text>
<text x="1017" y="216" fill="#87919d" font-family="monospace" font-size="10">{esc(peak["date"])}</text>
''']
    seen_months = set()
    for week_index, week in enumerate(weeks):
        if not week["contributionDays"]:
            continue
        first = min(week["contributionDays"], key=lambda day: day["date"])
        month_key = first["date"][:7]
        if month_key not in seen_months:
            seen_months.add(month_key)
            month = datetime.strptime(first["date"], "%Y-%m-%d").strftime("%b").upper()
            parts.append(f'<text x="{left + week_index * step}" y="143" fill="#a9b2bf" font-family="monospace" font-size="10">{month}</text>')
    for label, row in [("M", 1), ("W", 3), ("F", 5)]:
        parts.append(f'<text x="49" y="{top + row * step + 9}" fill="#818b99" font-family="monospace" font-size="10">{label}</text>')
    # Draw web-like connections only between adjacent active contribution days.
    # Every node and connection position is derived from the actual calendar data.
    for (week_index, row), point in points.items():
        if point["count"] <= 0:
            continue
        for prior_row in (row - 1, row, row + 1):
            prior = points.get((week_index - 1, prior_row))
            if prior and prior["count"] > 0:
                intensity = min(0.32, 0.08 + 0.025 * min(point["count"], prior["count"], 8))
                control_x = (prior["x"] + point["x"]) / 2
                control_y = (prior["y"] + point["y"]) / 2 - (6 if prior_row <= row else -6)
                parts.append(
                    f'<path d="M{prior["x"]:.1f} {prior["y"]:.1f} Q{control_x:.1f} {control_y:.1f} {point["x"]:.1f} {point["y"]:.1f}" '
                    f'fill="none" stroke="url(#line)" stroke-opacity="{intensity:.2f}" stroke-width="1.1"/>'
                )
    for (week_index, row), point in points.items():
        x = left + week_index * step
        y = top + row * step
        fill = PALETTE.get(point["level"], PALETTE["NONE"])
        if point["count"] > 0:
            parts.append(f'<rect x="{x-2}" y="{y-2}" width="{cell+4}" height="{cell+4}" rx="4" fill="{fill}" opacity=".15"/>')
        parts.append(
            f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{fill}" stroke="#ffffff" stroke-opacity=".05">'
            f'<title>{esc(point["date"])}: {point["count"]} contribution{"s" if point["count"] != 1 else ""}</title></rect>'
        )
    parts.append('<text x="48" y="349" fill="#8f99a6" font-family="monospace" font-size="9">LESS</text>')
    for i, level in enumerate(["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]):
        parts.append(f'<rect x="{83+i*19}" y="339" width="12" height="12" rx="3" fill="{PALETTE[level]}"/>')
    parts.append(f'''<text x="48" y="390" fill="#858e9a" font-family="monospace" font-size="10">WEB LINKS = ADJACENT ACTIVE DAYS · CELL = ONE REAL DAY</text>
<text x="1150" y="402" fill="#737d89" text-anchor="end" font-family="monospace" font-size="9">UPDATED {esc(updated)}</text>
</svg>''')
    return "\n".join(parts)

def make_telemetry(user, updated):
    calendar = user["contributionsCollection"]["contributionCalendar"]
    metrics = [
        ("CONTRIBUTIONS / 12 MONTHS", f'{calendar["totalContributions"]:,}', "Actual GitHub contribution calendar", "#70e2db"),
        ("PUBLIC REPOSITORIES", f'{user["repositories"]["totalCount"]:,}', "Public repositories", "#8dcde9"),
        ("FOLLOWERS", f'{user["followers"]["totalCount"]:,}', "GitHub followers", "#c4a8e9"),
    ]
    cards = []
    for index, (label, value, note, accent) in enumerate(metrics):
        x = 40 + index * 375
        cards.append(f'''<rect x="{x}" y="79" width="350" height="98" rx="12" fill="#20252c" stroke="#3b4652"/>
<rect x="{x}" y="79" width="4" height="98" rx="2" fill="{accent}"/>
<text x="{x+19}" y="105" fill="#9ca5b1" font-family="monospace" font-size="10">{esc(label)}</text>
<text x="{x+19}" y="143" fill="#f2f4f7" font-family="Arial,Helvetica,sans-serif" font-size="30" font-weight="700">{esc(value)}</text>
<text x="{x+19}" y="163" fill="#828c99" font-family="Arial,Helvetica,sans-serif" font-size="10">{esc(note)}</text>''')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="225" viewBox="0 0 1200 225" role="img" aria-labelledby="title desc">
<title id="title">Live GitHub telemetry for {esc(user["login"])}</title>
<desc id="desc">Real contribution, public repository and follower counts generated {esc(updated)}.</desc>
<defs><linearGradient id="outer" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#39d7d0"/><stop offset=".48" stop-color="#8dcde9"/><stop offset="1" stop-color="#d7a7df"/></linearGradient></defs>
<rect width="1200" height="225" rx="20" fill="url(#outer)"/><rect x="14" y="14" width="1172" height="197" rx="16" fill="#17191d" stroke="#e5e2ed" stroke-opacity=".65"/>
<text x="40" y="50" fill="#f4f6f8" font-family="Arial,Helvetica,sans-serif" font-size="21" font-weight="700">GITHUB TELEMETRY</text>
<text x="1158" y="49" fill="#9ca5b1" text-anchor="end" font-family="monospace" font-size="10">UPDATED {esc(updated)}</text>
{"".join(cards)}
</svg>'''

def main():
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    user = fetch_profile()
    ASSETS.mkdir(parents=True, exist_ok=True)
    calendar = user["contributionsCollection"]["contributionCalendar"]
    (ASSETS / "contribution-galaxy.svg").write_text(make_galaxy(user, updated), encoding="utf-8")
    (ASSETS / "github-telemetry.svg").write_text(make_telemetry(user, updated), encoding="utf-8")
    print(f"Generated contribution network: {calendar['totalContributions']} actual contributions.")
    print(f"Generated public repository and follower telemetry for {LOGIN} at {updated}.")

if __name__ == "__main__":
    main()
