# PlayAndPatch Custom Calendar

A customizable, automatically refreshed calendar built from the official [PlayAndPatch calendar](https://playandpatch.com/calendar). Choose the event categories you want, then subscribe to a generated iCalendar (ICS) feed in your calendar app. The project also includes an interactive monthly calendar on its landing page.

**Live calendar:** https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/  
**Original calendar:** https://playandpatch.com/calendar

## Features

- **Choose your categories:** Select any combination of the eight PlayAndPatch event categories.
- **Permanent subscription links:** Each non-empty category combination has its own ICS feed URL.
- **Sale is optional:** Sale is unchecked by default because Sale events can make a calendar look cluttered. You can enable it at any time.
- **Interactive monthly calendar:** Browse months, jump to today, filter events by category, and select an event to view its details and original event link (when supplied by the source).
- **Multi-day event bars:** Events spanning multiple days are shown as continuous bars across the relevant dates, with bars segmented at week boundaries.
- **Automatic updates:** GitHub Actions retrieves the source calendar and republishes the feeds and interactive calendar data every three hours.
- **Responsive landing page:** The category selector and calendar adapt to smaller screens.

## Event categories

The landing page provides these eight categories:

| Category | Feed key |
|---|---|
| Game releases | `releases` |
| Showcase | `showcase` |
| Festival | `festival` |
| Convention | `convention` |
| Awards | `awards` |
| Esports | `esports` |
| Update | `update` |
| Sale | `sale` |

All categories except **Sale** are selected by default on the landing page. The Sale information marker explains why it is off by default.

## How event filtering works

The project downloads the English PlayAndPatch iCalendar feed:

`https://playandpatch.com/calendar.ics?lang=en`

For a selected category combination, an event is included when its category metadata matches at least one selected category. The Sale category has an additional rule:

- Sale/Sales events are excluded whenever Sale is not selected, even if the event also has another category.
- When Sale is selected, Sale/Sales events can be included in the matching feed.
- Events without category metadata are retained in the legacy default `calendar.ics` feed for compatibility with the previous default feed. They are not included in the generated category-combination feeds.

The refresh script checks that category metadata is present and that the expected categories are represented in the source feed. If that validation fails, the workflow stops instead of silently publishing feeds from an unexpected source format.

## Available calendar feeds

The project pre-generates one feed for every **non-empty combination** of the eight categories:

`2^8 - 1 = 255` feeds.

Feed files are published in `docs/calendars/`. Their filenames use the selected category keys joined with hyphens. For example:

- `calendars/releases-showcase.ics` — Game releases and Showcase.
- `calendars/awards-esports.ics` — Esports and Awards.
- `calendars/all.ics` — all eight categories, including Sale.

The original default feed URL is also kept for compatibility:

- **Default feed (all categories except Sale):** https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/calendar.ics

This default feed includes uncategorized events as described above. To create a feed with a different selection, use the landing page; it builds the matching permanent URL and provides a copy button.

## Using the calendar

1. Open the [custom calendar landing page](https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/).
2. Select the categories you want. Use **Select all** or **Clear** to change the selection quickly.
3. Copy the subscription URL shown on the page, or open the generated ICS file.
4. In your calendar application, choose its option to **subscribe to a calendar by URL** and paste the URL.

**Subscribe rather than import** if you want to receive future changes. Importing an ICS file usually creates a one-time copy; it does not keep itself synchronized with the published feed. Calendar applications control how often they fetch subscribed calendars, so updates may not appear immediately after this project republishes a feed.

The interactive calendar on the landing page is a separate view of the source events. Its category checkboxes on the left determine which categories are included in the generated subscription URL and which categories are available to display. The filter pills above the calendar let you narrow the visible events further. Events without category metadata are retained in the legacy ICS feed but are not shown in the interactive calendar's category filters.

## Automatic refresh and deployment

The GitHub Actions workflow is configured to run:

- **On a schedule:** every three hours, at 17 minutes past the hour (UTC).
- **Manually:** through the workflow's `workflow_dispatch` option.
- **On selected pushes to `main`:** when `refresh_calendar.py`, `requirements.txt`, the workflow file, or `docs/index.html` changes.

Each run installs the Python dependencies, downloads and validates the source ICS feed, generates the filtered ICS files and `calendar-events.json`, and deploys the contents of `docs/` to GitHub Pages.

The three-hour schedule describes when this project republishes its feeds. It does **not** control when Google Calendar, Outlook, Apple Calendar, or another calendar application refreshes a subscribed feed.

## Repository structure

```text
.
├── .github/
│   └── workflows/
│       └── refresh-calendar.yml   # Scheduled refresh and GitHub Pages deployment
├── docs/
│   ├── index.html                  # Landing page, category selector and interactive calendar
│   ├── calendar.ics                # Legacy default feed (generated)
│   ├── calendar-events.json        # Interactive calendar data (generated)
│   └── calendars/                  # 255 generated category-combination feeds
├── refresh_calendar.py             # Fetches, validates, filters and publishes calendar data
├── requirements.txt                # Python dependencies
└── README.md
```

Generated files in `docs/` are recreated by the workflow; the source of the filtering and publishing logic is `refresh_calendar.py`.

## Run the refresh locally

The project uses Python. To run the refresh script locally:

```bash
python -m pip install -r requirements.txt
python refresh_calendar.py
```

The script writes the generated calendar files into `docs/`. It can also use a different source ICS URL through the `SOURCE_ICS_URL` environment variable.

## Links

- [Custom calendar landing page](https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/)
- [Default all-non-Sale ICS feed](https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/calendar.ics)
- [Original PlayAndPatch calendar](https://playandpatch.com/calendar)
- [GitHub repository](https://github.com/Biglitttle125/PlayAndPatch-No-Sales-Calendar)
