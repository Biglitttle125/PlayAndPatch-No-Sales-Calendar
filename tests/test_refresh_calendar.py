import json
import os
import tempfile
import unittest
from unittest.mock import patch
from datetime import date
from pathlib import Path

from icalendar import Calendar, Event

import refresh_calendar as refresh


def make_event(categories=None, url=None, uid="event-1"):
    event = Event()
    event.add("uid", uid)
    event.add("summary", "Test event")
    event.add("dtstart", date(2026, 11, 5))
    event.add("dtend", date(2026, 11, 6))
    if categories is not None:
        event.add("categories", categories)
    if url is not None:
        event.add("url", url)
    return event


class FeedFilteringTests(unittest.TestCase):
    def test_sale_event_with_other_category_is_excluded_without_sale(self):
        event = make_event(["Sale", "Showcase"])
        self.assertFalse(refresh.should_include_event(event, {"showcase"}))

    def test_sale_event_is_included_when_sale_selected(self):
        event = make_event(["Sale", "Showcase"])
        self.assertTrue(refresh.should_include_event(event, {"sale"}))

    def test_regular_event_matches_selected_category(self):
        event = make_event(["Showcase"])
        self.assertTrue(refresh.should_include_event(event, {"showcase"}))
        self.assertFalse(refresh.should_include_event(event, {"festival"}))

    def test_uncategorized_event_only_appears_in_default_non_sale_feed(self):
        event = make_event()
        default_keys = {key for key, _, _ in refresh.CATEGORY_OPTIONS if key != "sale"}
        self.assertTrue(refresh.should_include_event(event, default_keys))
        self.assertFalse(refresh.should_include_event(event, {"showcase"}))
        self.assertFalse(refresh.should_include_event(event, set()))

    def test_all_255_non_empty_combinations_can_be_written(self):
        calendar = Calendar()
        calendar.add("version", "2.0")
        events = [make_event(["Showcase"]), make_event(["Sale"])]
        for event in events:
            calendar.add_component(event)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            for mask in range(1, 1 << len(refresh.CATEGORY_OPTIONS)):
                selected = {
                    key for index, (key, _, _) in enumerate(refresh.CATEGORY_OPTIONS)
                    if mask & (1 << index)
                }
                slug = "all" if len(selected) == len(refresh.CATEGORY_OPTIONS) else "-".join(
                    key for key, _, _ in refresh.CATEGORY_OPTIONS if key in selected
                )
                refresh.write_feed(calendar, events, selected, output / f"{slug}.ics")
            self.assertEqual(len(list(output.glob("*.ics"))), 255)



class EventChangeDetectionTests(unittest.TestCase):
    def sample(self, uid, title="Event", start="2026-12-01", categories=None):
        return {
            "id": uid, "title": title, "start": start, "end": "2026-12-02",
            "allDay": True, "categories": categories or ["showcase"],
            "description": "", "url": "https://example.com/event",
        }

    def test_detects_added_removed_and_modified_events(self):
        previous = [
            self.sample("unchanged"),
            self.sample("changed", title="Old title"),
            self.sample("removed"),
        ]
        current = [
            self.sample("unchanged"),
            self.sample("changed", title="New title"),
            self.sample("added"),
        ]
        changes = refresh.event_changes(previous, current)
        self.assertEqual([item["event"]["id"] for item in changes["added"]], ["added"])
        self.assertEqual([item["event"]["id"] for item in changes["removed"]], ["removed"])
        self.assertEqual(changes["modified"][0]["event"]["id"], "changed")
        self.assertEqual(changes["modified"][0]["changes"][0]["field"], "Title")

    def test_preserves_history_when_next_refresh_has_no_changes(self):
        old = self.sample("same")
        history = {"history": [{"updatedAt": "2026-11-27T00:00:00Z", "counts": {
            "added": 1, "modified": 0, "removed": 0
        }, "added": [{"event": self.sample("previously-added")}], "modified": [], "removed": []}]}
        result = refresh.write_change_history([old], [old], history)
        self.assertEqual(len(result["history"]), 1)
        self.assertEqual(result["history"][0]["counts"]["added"], 1)

    def test_limits_history_to_ten_entries(self):
        history = {"history": [{"updatedAt": str(index)} for index in range(12)]}
        result = refresh.write_change_history([], [], history)
        self.assertEqual(len(result["history"]), 10)

    def test_first_snapshot_establishes_baseline_without_false_additions(self):
        result = refresh.write_change_history(None, [self.sample("first")], None)
        self.assertFalse(result["baselineAvailable"])
        self.assertEqual(result["history"], [])

class EventUrlTests(unittest.TestCase):
    def test_accepts_http_and_https_urls(self):
        self.assertEqual(refresh.safe_event_url("https://example.com/event"), "https://example.com/event")
        self.assertEqual(refresh.safe_event_url("http://example.com/event"), "http://example.com/event")

    def test_rejects_non_http_schemes_and_relative_urls(self):
        for value in ("javascript:alert(1)", "data:text/html,hello", "file:///etc/passwd", "/relative/path", "example.com"):
            with self.subTest(value=value):
                self.assertEqual(refresh.safe_event_url(value), "")

    def test_rejects_malformed_urls_and_embedded_credentials(self):
        for value in ("https://", "https://example.com:bad/", "https://user:pass@example.com/"):
            with self.subTest(value=value):
                self.assertEqual(refresh.safe_event_url(value), "")

    def test_interactive_json_contains_only_safe_event_urls(self):
        events = [
            make_event(["Showcase"], "https://example.com/good", "good"),
            make_event(["Showcase"], "javascript:alert(1)", "bad"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            original_cwd = Path.cwd()
            try:
                os.chdir(directory)
                with patch.object(refresh, "fetch_published_json", side_effect=[None, None]):
                    refresh.write_calendar_data(events)
                data = json.loads(Path("docs/calendar-events.json").read_text(encoding="utf-8"))
            finally:
                os.chdir(original_cwd)
        self.assertEqual(data[0]["url"], "https://example.com/good")
        self.assertEqual(data[1]["url"], "")


if __name__ == "__main__":
    unittest.main()
