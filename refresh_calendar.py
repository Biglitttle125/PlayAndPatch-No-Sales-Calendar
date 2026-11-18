#!/usr/bin/env python3
"""Fetch PlayAndPatch and publish selectable, auto-updating category feeds."""
from __future__ import annotations

import copy
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
FEEDS_DIR = Path("docs/calendars")
EXCLUDED_CATEGORIES = {"sale", "sales"}

# Stable URL keys and the category names used by PlayAndPatch.
CATEGORY_OPTIONS = [
    ("releases", "Game Releases"),
    ("showcase", "Showcase"),
    ("festival", "Festival"),
    ("convention", "Convention"),
    ("awards", "Awards"),
    ("esports", "Esports"),
    ("update", "Update"),
]


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


def write_feed(calendar, events, selected_categories, filename):
    """Write a feed containing selected categories; all-category feed keeps uncategorized events."""
    selected = {name.casefold() for name in selected_categories}
    all_selected = len(selected) == len(CATEGORY_OPTIONS)
    output_calendar = copy.deepcopy(calendar)

    for event in list(output_calendar.subcomponents):
        if event.name != "VEVENT":
            continue
        names = {name.strip().casefold() for name in category_names(event)}
        if names & EXCLUDED_CATEGORIES:
            output_calendar.subcomponents.remove(event)
        elif not all_selected and not (names & selected):
            output_calendar.subcomponents.remove(event)

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_bytes(output_calendar.to_ical())
    return sum(
        1 for event in events
        if (category_names(event) and
            not ({name.casefold() for name in category_names(event)} & EXCLUDED_CATEGORIES) and
            (all_selected or bool({name.casefold() for name in category_names(event)} & selected)))
        or (all_selected and not category_names(event))
    )


def main():
    response = requests.get(
        SOURCE_URL, timeout=45,
        headers={"User-Agent": "PlayAndPatchCalendarFilter/1.0"},
    )
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

    if not categories_seen:
        raise RuntimeError("No CATEGORIES metadata was found; refusing to publish an unfiltered calendar.")
    if not excluded:
        raise RuntimeError("No Sale/Sales events were detected. Check the source feed before publishing.")

    available = {name.casefold() for _, name in CATEGORY_OPTIONS}
    missing = available - categories_seen
    if missing:
        raise RuntimeError(
            "Expected categories missing from source feed: " + ", ".join(sorted(missing))
        )

    # The original calendar.ics remains the default: everything except Sale/Sales.
    all_names = [name for _, name in CATEGORY_OPTIONS]
    kept = write_feed(calendar, events, all_names, OUTPUT)

    # Pre-generate all 2^7 combinations so each selected set has a stable
    # subscription URL that can keep updating on GitHub Pages.
    generated = 0
    for mask in range(1, 1 << len(CATEGORY_OPTIONS)):
        chosen = [
            (key, name)
            for index, (key, name) in enumerate(CATEGORY_OPTIONS)
            if mask & (1 << index)
        ]
        keys = [key for key, _ in chosen]
        names = [name for _, name in chosen]
        slug = "all" if len(chosen) == len(CATEGORY_OPTIONS) else "-".join(keys)
        write_feed(calendar, events, names, FEEDS_DIR / f"{slug}.ics")
        generated += 1

    print(f"Published default feed with {kept} events; excluded {len(excluded)} Sale/Sales events.")
    print(f"Generated {generated} selectable category feeds.")
    print("Categories found: " + ", ".join(sorted(categories_seen)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
