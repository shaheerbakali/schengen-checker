#!/usr/bin/env python3
"""
Schengen Slot Checker — one-shot version for GitHub Actions.
GitHub runs this every 5 minutes. If a slot is found, it fires
a push notification to your phone via ntfy.sh.
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

# Your ntfy topic — must match what you subscribed to in the ntfy app
# Set this as a GitHub Secret called NTFY_TOPIC (see README)
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "schengen-lenovo-alerts")

# Your webhook.site URL for a live log (optional but useful)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "https://webhook.site/4a1f1e17-a6b4-40d4-8906-9022f56980d2")

URL = "https://schengenappointments.com/in/london/tourism"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ── Scraper ───────────────────────────────────────────────────────────────────

def check_slots():
    resp = requests.get(URL, headers=HEADERS, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    found = []
    for row in soup.select("tbody tr"):
        th = row.find("th")
        if not th:
            continue
        country = th.get_text(strip=True)
        if not country:
            continue

        for td in row.find_all("td"):
            a = td.find("a", class_=lambda c: c and "text-success" in c)
            if a:
                slot_text = a.get_text(" ", strip=True)
                link = a.get("href", URL)
                if not link.startswith("http"):
                    link = "https://schengenappointments.com" + link
                found.append({"country": country, "slots": slot_text, "link": link})
                break

    return found

# ── Notifications ─────────────────────────────────────────────────────────────

def send_ntfy(country, slots, link):
    r = requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        headers={
            "Title":    f"Schengen slot OPEN: {country}",
            "Priority": "urgent",
            "Tags":     "passport_control,rotating_light",
            "Click":    link,
        },
        data=f"{slots} available for {country}\n\nBook now: {link}",
        timeout=10,
    )
    print(f"  ntfy.sh -> {r.status_code}")


def send_webhook(country, slots, link):
    try:
        requests.post(
            WEBHOOK_URL,
            json={
                "event":   "SLOT_AVAILABLE",
                "country": country,
                "slots":   slots,
                "link":    link,
                "time":    datetime.now().isoformat(),
            },
            timeout=10,
        )
    except Exception:
        pass   # webhook is optional, don't crash if it fails

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print(f"[{datetime.utcnow().isoformat()}] Checking {URL} ...")

    try:
        slots = check_slots()
    except Exception as e:
        print(f"ERROR fetching page: {e}")
        sys.exit(1)

    if not slots:
        print("No slots available.")
        sys.exit(0)

    print(f"*** {len(slots)} slot(s) found! ***")
    for s in slots:
        print(f"  {s['country']} — {s['slots']} — {s['link']}")
        send_ntfy(s["country"], s["slots"], s["link"])
        send_webhook(s["country"], s["slots"], s["link"])

    # Exit code 0 = success either way
    sys.exit(0)


if __name__ == "__main__":
    main()