#!/usr/bin/env python3
"""Fetch the PlayAndPatch calendar and publish every event except Sale/Sales."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from icalendar import Calendar

SOURCE_URL = os.environ.get(
    "SOURCE_ICS_URL",
    "https://playandpatch.com/calendar.ics?lang=en",
)
OUTPUT = Path("docs/calendar.ics")
EXCLUDED_CATEGORIES = {"sale", "sales"}


def category_names(event):
    raw = event.get("CATEGORIES")
    if raw is None:
        return []
    values = getattr(raw, "cats", None)
    if values is None:
        values = raw if isinstance(raw, list) else [raw]
    result = []
    for value in values:
        if isinstance(value, bytes):
            value = value.decode("utf-8", "replace")
        result.extend(part.strip() for part in str(value).split(",") if part.strip())
    return result


def main():
    response = requests.get(SOURCE_URL, timeout=45, headers={"User-Agent": "PlayAndPatchCalendarFilter/1.0"})
    response.raise_for_status()
    payload = response.content
    if b"BEGIN:VCALENDAR" not in payload[:4096]:
        raise RuntimeError("The source did not return a valid iCalendar feed.")

    calendar = Calendar.from_ical(payload)
    events = [item for item in calendar.subcomponents if item.name == "VEVENT"]
    if not events:
        raise RuntimeError("The source calendar contains no VEVENT entries.")

    categories_seen = set()
    excluded = []
    for event in events:
        categories = category_names(event)
        categories_seen.update(category.strip().casefold() for category in categories)
        if any(category.strip().casefold() in EXCLUDED_CATEGORIES for category in categories):
            excluded.append(event)

    # Fail rather than accidentally publish an unfiltered feed if the source
    # changes its category representation or the Sale category disappears.
    if not categories_seen:
        raise RuntimeError("No CATEGORIES metadata was found; refusing to publish an unfiltered calendar.")
    if not excluded:
        raise RuntimeError(
            "No Sale/Sales events were detected. Check the source feed's category format before publishing."
        )

    for event in excluded:
        calendar.subcomponents.remove(event)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_bytes(calendar.to_ical())

    kept = len(events) - len(excluded)
    print(f"Published {kept} events; excluded {len(excluded)} Sale/Sales events.")
    print("Categories found: " + ", ".join(sorted(categories_seen)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
