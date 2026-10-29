#!/usr/bin/env python3
"""Render a monochrome contribution heatmap as SVG.

Reads the contribution calendar for a user via the GitHub GraphQL API and
writes a self-contained SVG. Stdlib only, so a runner needs no install step.

Env:
    GITHUB_TOKEN  token used for the API call (required)
    GH_LOGIN      user to render (default: MrBolas)
    OUT           output path (default: heatmap.svg)
"""

import json
import os
import sys
import urllib.request
from datetime import date

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { date contributionCount contributionLevel }
        }
      }
    }
  }
}
"""

LEVELS = ["#eceef1", "#c9cfd8", "#98a2b0", "#5c6675", "#16181d"]
LEVEL_INDEX = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

CELL, GAP = 11, 3
STEP = CELL + GAP
PAD = 16
LEFT, TOP = PAD + 38, PAD + 24
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def fetch_calendar(token, login):
    body = json.dumps({"query": QUERY, "variables": {"login": login}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-heatmap",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    if "errors" in payload:
        raise SystemExit(f"GraphQL error: {payload['errors']}")
    return payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def esc(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render(calendar):
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    if not weeks:
        raise SystemExit("no contribution weeks returned")
    if total == 0:
        raise SystemExit("total contributions is 0 - refusing to commit an empty heatmap")

    width = LEFT + len(weeks) * STEP - GAP + PAD + 10
    height = TOP + 7 * STEP - GAP + PAD + 34

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{esc(str(total))} contributions in the last 12 months">',
        f"<title>{total} contributions in the last 12 months</title>",
        # White panel: GitHub renders images on both light and dark backgrounds, and the
        # darkest cells disappear without one. Matches the CV's document treatment.
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" '
        f'fill="#ffffff" stroke="#d9dce2"/>',
        f'<g font-family="{FONT}" font-size="11" fill="#5c6470">',
    ]

    last_month = None
    last_label_col = -99
    for i, week in enumerate(weeks):
        first_day = week["contributionDays"][0]["date"]
        month = int(first_day[5:7]) - 1
        if month != last_month:
            if i - last_label_col >= 3:
                x = LEFT + i * STEP
                parts.append(f'<text x="{x}" y="{PAD + 4}">{MONTHS[month]}</text>')
                last_label_col = i
            last_month = month

    for row, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        y = TOP + row * STEP + CELL - 2
        parts.append(f'<text x="{PAD}" y="{y}">{label}</text>')

    for col, week in enumerate(weeks):
        for row, day in enumerate(week["contributionDays"]):
            level = LEVEL_INDEX.get(day["contributionLevel"], 0)
            x = LEFT + col * STEP
            y = TOP + row * STEP
            parts.append(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" '
                f'fill="{LEVELS[level]}"><title>{day["date"]}: '
                f'{day["contributionCount"]}</title></rect>'
            )

    parts.append("</g>")
    caption_y = height - PAD - 2
    parts.append(
        f'<text x="{PAD}" y="{caption_y}" font-family="{FONT}" font-size="12" '
        f'fill="#5c6470">{total:,} contributions in the last 12 months</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def main():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required")
    login = os.environ.get("GH_LOGIN", "MrBolas")
    out = os.environ.get("OUT", "heatmap.svg")

    svg = render(fetch_calendar(token, login))
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(svg + "\n")
    print(f"wrote {out} ({len(svg)} bytes, generated {date.today()})")


if __name__ == "__main__":
    main()
