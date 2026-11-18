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

# Keys are used in permanent feed URLs. The final entry supports both
# spellings that may be used by the source calendar.
CATEGORY_OPTIONS = [
    ("releases", "Game Releases", {"game releases"}),
    ("showcase", "Showcase", {"showcase"}),
    ("festival", "Festival", {"festival"}),
    ("convention", "Convention", {"convention"}),
    ("awards", "Awards", {"awards"}),
    ("esports", "Esports", {"esports"}),
    ("update", "Update", {"update"}),
    ("sale", "Sale", {"sale", "sales"}),
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


def write_feed(calendar, events, selected_keys, filename):
    """Write a feed containing events matching at least one selected category."""
    selected = set(selected_keys)
    sale_aliases = {"sale", "sales"}
    selected_aliases = set()
    for key, _label, aliases in CATEGORY_OPTIONS:
        if key in selected:
            selected_aliases.update(aliases)

    non_sale_keys = {key for key, _label, _aliases in CATEGORY_OPTIONS if key != "sale"}
    # Keep uncategorized events in the default all-non-Sales feed, as before.
    include_uncategorized = selected == non_sale_keys
    output_calendar = copy.deepcopy(calendar)

    for event in list(output_calendar.subcomponents):
        if event.name != "VEVENT":
            continue
        names = {name.strip().casefold() for name in category_names(event)}
        has_sale = bool(names & sale_aliases)

        # Sale/Sales events are excluded unless the Sale checkbox is selected.
        if has_sale and "sale" not in selected:
            output_calendar.subcomponents.remove(event)
        elif names and not (names & selected_aliases):
            output_calendar.subcomponents.remove(event)
        elif not names and not include_uncategorized:
            output_calendar.subcomponents.remove(event)

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_bytes(output_calendar.to_ical())
    return sum(
        1 for event in events
        if (
            (bool(set(name.casefold() for name in category_names(event)) & sale_aliases)
             and "sale" in selected)
            or (
                bool(set(name.casefold() for name in category_names(event)) & selected_aliases)
                and not (
                    bool(set(name.casefold() for name in category_names(event)) & sale_aliases)
                    and "sale" not in selected
                )
            )
            or (not category_names(event) and include_uncategorized)
        )
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
    for event in events:
        categories_seen.update(category.strip().casefold() for category in category_names(event))

    if not categories_seen:
        raise RuntimeError("No CATEGORIES metadata was found; refusing to publish category feeds.")

    expected = set().union(*(aliases for _, _, aliases in CATEGORY_OPTIONS))
    missing = expected - categories_seen
    # PlayAndPatch currently labels the category "Sale" (singular).
    # Accept that as satisfying the optional Sale checkbox; "Sales" is
    # retained only as a compatibility alias for feeds that use that spelling.
    if "sale" in categories_seen:
        missing.discard("sales")
    if missing:
        raise RuntimeError(
            "Expected categories missing from source feed: " + ", ".join(sorted(missing))
        )

    # The legacy calendar.ics URL remains the default: all categories except Sale.
    default_keys = {key for key, _, _ in CATEGORY_OPTIONS if key != "sale"}
    kept = write_feed(calendar, events, default_keys, OUTPUT)

    # Pre-generate every non-empty combination of all eight categories (255 feeds).
    generated = 0
    for mask in range(1, 1 << len(CATEGORY_OPTIONS)):
        chosen = [
            key for index, (key, _, _) in enumerate(CATEGORY_OPTIONS)
            if mask & (1 << index)
        ]
        slug = "all" if len(chosen) == len(CATEGORY_OPTIONS) else "-".join(chosen)
        write_feed(calendar, events, set(chosen), FEEDS_DIR / f"{slug}.ics")
        generated += 1

    print(f"Published default feed with {kept} events; Sale/Sales excluded by default.")
    print(f"Generated {generated} selectable category feeds.")
    print("Categories found: " + ", ".join(sorted(categories_seen)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
