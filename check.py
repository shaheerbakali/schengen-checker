#!/usr/bin/env python3
"""
Schengen Slot Checker — GitHub Actions version.
- Only watches specific preferred countries
- Only notifies when 2+ slots are available on the SAME day
- Sends push notification via ntfy.sh
"""

import os
import re
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# ── Config ────────────────────────────────────────────────────────────────────

NTFY_TOPIC  = os.environ.get("NTFY_TOPIC",  "schengen-lenovo-alerts")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")

# Only care about these countries (case-insensitive match)
PREFERRED_COUNTRIES = [
    "Netherlands",
    "Italy",
    "Austria",
    "Czechia",
    "Malta",
    "Portugal",
    "Norway",
    "Sweden",
]

# Minimum slots needed ON THE SAME DAY to trigger a notification
MIN_SLOTS_SAME_DAY = 2

BASE_URL = "https://schengenappointments.com"
MAIN_URL = f"{BASE_URL}/in/london/tourism"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_soup(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def is_preferred(country_name):
    for pref in PREFERRED_COUNTRIES:
        if pref.lower() in country_name.lower():
            return True
    return False


# ── Step 1: Scan main page for countries that have ANY slots ──────────────────

def get_countries_with_slots():
    """
    Returns list of dicts:
        { "country": "Italy", "link": "https://.../italy/tourism" }
    for countries that show any available slots on the main overview page.
    """
    print(f"Fetching main page: {MAIN_URL}")
    soup = get_soup(MAIN_URL)

    available = []
    for row in soup.select("tbody tr"):
        th = row.find("th")
        if not th:
            continue
        country = th.get_text(strip=True)
        if not country or not is_preferred(country):
            continue

        # A slot is available if any <td> contains a link with text like "1 +" or "3 +"
        # These links do NOT contain "No availability" and DO contain the word "slots"
        for td in row.find_all("td"):
            text = td.get_text(strip=True)
            # Look for patterns like "1 +slots", "2 +slots", "3+slots" etc.
            if re.search(r'\d+\s*\+?\s*slots?', text, re.IGNORECASE):
                # Get the booking link from the anchor
                a = td.find("a", href=True)
                link = a["href"] if a else ""
                if link and not link.startswith("http"):
                    link = BASE_URL + link
                if not link:
                    link = f"{BASE_URL}/in/london/{country.lower()}/tourism"
                available.append({"country": country, "link": link})
                print(f"  -> {country} has slots on overview page. Checking details...")
                break

    return available


# ── Step 2: Check country detail page for 2+ slots on same day ───────────────

def get_best_day(country_link):
    """
    Visit the country's detail page and find dates with MIN_SLOTS_SAME_DAY or more.
    Returns list of dicts:
        { "date": "11 Jun (Thu)", "slots": 3 }
    """
    print(f"  Fetching detail: {country_link}")
    try:
        soup = get_soup(country_link)
    except Exception as e:
        print(f"  ERROR fetching detail page: {e}")
        return []

    good_days = []

    # The detail page has a table with rows per date showing slot counts
    # Look for any table row that has a date and a slot number
    for row in soup.select("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue

        row_text = row.get_text(" ", strip=True)

        # Skip header rows
        if "date" in row_text.lower() and "appointment" in row_text.lower():
            continue

        # Try to find a slot count number in the row
        # Look for patterns like "2 slots available", "3 slots", "2 appointments"
        slot_match = re.search(r'(\d+)\s+slots?\s+available', row_text, re.IGNORECASE)
        if not slot_match:
            slot_match = re.search(r'(\d+)\s+appointments?\s+available', row_text, re.IGNORECASE)
        if not slot_match:
            # Also try just a standalone number in a cell next to a date
            for cell in cells:
                cell_text = cell.get_text(strip=True)
                if re.fullmatch(r'\d+', cell_text):
                    slot_count = int(cell_text)
                    if slot_count >= MIN_SLOTS_SAME_DAY:
                        # Find date in same row
                        date_str = cells[0].get_text(strip=True)
                        good_days.append({"date": date_str, "slots": slot_count})
            continue

        slot_count = int(slot_match.group(1))
        if slot_count >= MIN_SLOTS_SAME_DAY:
            date_str = cells[0].get_text(strip=True)
            good_days.append({"date": date_str, "slots": slot_count})

    return good_days


# ── Notifications ─────────────────────────────────────────────────────────────

def send_ntfy(country, days, link):
    """Send urgent push notification to phone."""
    day_lines = "\n".join(
        f"  {d['date']}: {d['slots']} slots" for d in days
    )
    body = f"Dates with {MIN_SLOTS_SAME_DAY}+ slots:\n{day_lines}\n\nBook: {link}"

    print(f"  Sending ntfy to topic: {NTFY_TOPIC}")
    try:
        r = requests.post(
            f"https://ntfy.sh/{NTFY_TOPIC}",
            headers={
                "Title":    f"Schengen {country}: {days[0]['slots']} slots on {days[0]['date']}",
                "Priority": "urgent",
                "Tags":     "passport_control,rotating_light",
                "Click":    link,
            },
            data=body.encode("utf-8"),
            timeout=10,
        )
        print(f"  ntfy response: {r.status_code} {r.text[:80]}")
    except Exception as e:
        print(f"  ntfy ERROR: {e}")


def send_webhook(country, days, link):
    if not WEBHOOK_URL:
        return
    try:
        requests.post(
            WEBHOOK_URL,
            json={
                "event":   "SLOT_AVAILABLE",
                "country": country,
                "days":    days,
                "link":    link,
                "time":    datetime.now().isoformat(),
            },
            timeout=10,
        )
    except Exception:
        pass


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print(f"Schengen Checker  {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"Watching: {', '.join(PREFERRED_COUNTRIES)}")
    print(f"Minimum slots needed on same day: {MIN_SLOTS_SAME_DAY}")
    print(f"ntfy topic: {NTFY_TOPIC}")
    print("=" * 55)

    # Step 1: Find which preferred countries have any slots at all
    try:
        candidates = get_countries_with_slots()
    except Exception as e:
        print(f"FATAL: Could not fetch main page: {e}")
        sys.exit(1)

    if not candidates:
        print("No slots found for any preferred country. Done.")
        sys.exit(0)

    print(f"\n{len(candidates)} candidate(s) to inspect...")

    # Step 2: For each candidate, check if any day has 2+ slots
    notified = 0
    for c in candidates:
        good_days = get_best_day(c["link"])

        if not good_days:
            print(f"  {c['country']}: no day with {MIN_SLOTS_SAME_DAY}+ slots on same day. Skipping.")
            continue

        print(f"  {c['country']}: FOUND {len(good_days)} qualifying day(s)!")
        for d in good_days:
            print(f"    {d['date']}: {d['slots']} slots")

        send_ntfy(c["country"], good_days, c["link"])
        send_webhook(c["country"], good_days, c["link"])
        notified += 1

    if notified == 0:
        print("\nNo countries met the 2+ slots on same day requirement.")
    else:
        print(f"\nNotified for {notified} country/countries.")

    sys.exit(0)


if __name__ == "__main__":
    main()
