#!/usr/bin/env python3
"""Fetch PlayAndPatch and publish selectable, auto-updating category feeds."""
from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
import sys
from pathlib import Path
from urllib.parse import urlsplit

import requests
from icalendar import Calendar

SOURCE_URL = os.environ.get(
    "SOURCE_ICS_URL",
    "https://playandpatch.com/calendar.ics?lang=en",
)
FEEDS_DIR = Path("docs/calendars")
PUBLISHED_BASE_URL = "https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar"
CHANGE_HISTORY_LIMIT = 10

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


def should_include_event(event, selected_keys):
    """Return whether an event belongs in a selected category feed."""
    selected = set(selected_keys)
    selected_aliases = set()
    for key, _label, aliases in CATEGORY_OPTIONS:
        if key in selected:
            selected_aliases.update(aliases)

    names = {name.strip().casefold() for name in category_names(event)}
    has_sale = bool(names & {"sale", "sales"})
    non_sale_keys = {key for key, _label, _aliases in CATEGORY_OPTIONS if key != "sale"}
    include_uncategorized = selected == non_sale_keys

    # Sale/Sales events are excluded unless Sale is selected, even when
    # they also carry another selected category.
    if has_sale and "sale" not in selected:
        return False
    if names:
        return bool(names & selected_aliases)
    return include_uncategorized


def write_feed(calendar, events, selected_keys, filename):
    """Write a feed containing events matching at least one selected category."""
    output_calendar = copy.deepcopy(calendar)
    for event in list(output_calendar.subcomponents):
        if event.name == "VEVENT" and not should_include_event(event, selected_keys):
            output_calendar.subcomponents.remove(event)

    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_bytes(output_calendar.to_ical())
    return sum(1 for event in events if should_include_event(event, selected_keys))


def safe_event_url(value):
    """Return an absolute HTTP(S) URL, or an empty string for unsafe values."""
    if value is None:
        return ""
    candidate = str(value).strip()
    try:
        parsed = urlsplit(candidate)
        if parsed.scheme.casefold() not in {"http", "https"} or not parsed.hostname:
            return ""
        if parsed.username is not None or parsed.password is not None:
            return ""
        # Accessing .port also validates malformed port syntax.
        _ = parsed.port
    except (ValueError, TypeError):
        return ""
    return candidate


def event_json_value(value):
    """Convert an iCalendar date or datetime into a JSON-safe ISO string."""
    if value is None:
        return None
    value = getattr(value, "dt", value)
    return value.isoformat()


def build_calendar_data(events):
    """Convert source events into the JSON format used by the landing page."""
    category_map = {
        "game releases": "releases",
        "showcase": "showcase",
        "festival": "festival",
        "convention": "convention",
        "awards": "awards",
        "esports": "esports",
        "update": "update",
        "sale": "sale",
        "sales": "sale",
    }
    output = []
    for event in events:
        start_value = event_json_value(event.get("DTSTART"))
        end_value = event_json_value(event.get("DTEND"))
        if not start_value:
            continue
        start_obj = event.get("DTSTART").dt
        all_day = not hasattr(start_obj, "hour")
        if not end_value:
            end_value = start_value
        names = [name.casefold() for name in category_names(event)]
        categories = sorted({category_map[name] for name in names if name in category_map})
        url_value = safe_event_url(event.get("URL"))
        description_value = event.get("DESCRIPTION")
        output.append({
            "id": str(event.get("UID") or f"{start_value}-{event.get('SUMMARY', '')}"),
            "title": str(event.get("SUMMARY") or "Untitled event"),
            "start": start_value,
            "end": end_value,
            "allDay": all_day,
            "categories": categories,
            "description": str(description_value) if description_value else "",
            "url": url_value,
        })
    return output


def fetch_published_json(filename):
    """Read the last successfully deployed JSON file; only a 404 means no baseline."""
    url = f"{PUBLISHED_BASE_URL}/{filename}?refresh={int(datetime.now(timezone.utc).timestamp())}"
    response = requests.get(
        url, timeout=20,
        headers={"User-Agent": "PlayAndPatchCalendarFilter/1.0", "Cache-Control": "no-cache"},
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def event_changes(previous, current):
    """Compare event snapshots by UID and report additions, removals and field changes."""
    old_by_id = {event["id"]: event for event in previous or []}
    new_by_id = {event["id"]: event for event in current}
    added = [{"event": new_by_id[key]} for key in sorted(new_by_id.keys() - old_by_id.keys())]
    removed = [{"event": old_by_id[key]} for key in sorted(old_by_id.keys() - new_by_id.keys())]
    fields = [
        ("title", "Title"), ("start", "Start"), ("end", "End"),
        ("allDay", "All-day setting"), ("categories", "Categories"),
        ("description", "Description"), ("url", "Event link"),
    ]
    modified = []
    for key in sorted(old_by_id.keys() & new_by_id.keys()):
        old_event, new_event = old_by_id[key], new_by_id[key]
        differences = [
            {"field": label, "old": old_event.get(field), "new": new_event.get(field)}
            for field, label in fields
            if old_event.get(field) != new_event.get(field)
        ]
        if differences:
            modified.append({"event": new_event, "changes": differences})
    return {"added": added, "modified": modified, "removed": removed}


def write_change_history(previous_events, current_events, previous_history):
    """Keep the latest ten update summaries, including across refreshes with no changes."""
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    history = list((previous_history or {}).get("history", []))
    changes = event_changes(previous_events, current_events) if previous_events is not None else {
        "added": [], "modified": [], "removed": []
    }
    total = sum(len(changes[key]) for key in ("added", "modified", "removed"))
    if total:
        history.insert(0, {
            "updatedAt": now,
            "counts": {key: len(changes[key]) for key in ("added", "modified", "removed")},
            **changes,
        })
    history = history[:CHANGE_HISTORY_LIMIT]
    return {
        "lastCheckedAt": now,
        "baselineAvailable": previous_events is not None,
        "history": history,
    }


def write_calendar_data(events):
    """Publish the current event snapshot and a rolling history of detected changes."""
    current_events = build_calendar_data(events)
    previous_events = fetch_published_json("calendar-events.json")
    previous_history = fetch_published_json("calendar-changes.json")
    changes = write_change_history(previous_events, current_events, previous_history)

    target = Path("docs/calendar-events.json")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(current_events, ensure_ascii=False, indent=2), encoding="utf-8")
    (target.parent / "calendar-changes.json").write_text(
        json.dumps(changes, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Published interactive calendar data with {len(current_events)} events.")
    if not changes["baselineAvailable"]:
        print("No previous published event snapshot was available; change tracking baseline established.")
    else:
        latest = changes["history"][0] if changes["history"] else None
        print("Detected changes in this refresh: " + str(sum(latest["counts"].values()) if latest else 0))


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
    write_calendar_data(events)
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

    print("Sale/Sales events are excluded from feeds unless Sale is selected.")
    print(f"Generated {generated} selectable category feeds.")
    print("Categories found: " + ", ".join(sorted(categories_seen)))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
