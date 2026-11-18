# PlayAndPatch — Custom Calendar

This repository publishes subscription-ready iCalendar feeds based on the official PlayAndPatch calendar.

## How it works

- Fetches `https://playandpatch.com/calendar.ics?lang=en`.
- Supports all eight PlayAndPatch categories: Game Releases, Showcase, Festival, Convention, Awards, Esports, Update, and Sale.
- Sale is unchecked by default on the landing page, but can be selected to include Sale/Sales events.
- Publishes a separate feed for every non-empty combination of the eight categories (255 feeds total).
- Keeps the original `calendar.ics` URL as the default feed with all non-Sales categories selected.
- The landing page lets visitors select categories and gives them the matching permanent subscription URL.
- GitHub Actions refreshes every feed every three hours and can also be started manually.

For a selected category combination, an event is included when it matches at least one selected category. Sale/Sales events are excluded unless Sale is selected. The default all-non-Sales feed continues to retain uncategorized events, as the original feed did.

The job intentionally fails if expected category metadata is missing, preventing an unexpected source-feed format from silently publishing incomplete calendars.

## Calendar URLs

- Landing page: `https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/`
- Default all-non-Sales feed: `https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/calendar.ics`

Use the landing page to select categories and copy the resulting subscription URL. Subscribe by URL in your calendar app; do not import the file if you want future updates. Calendar applications decide how often they refresh subscribed feeds.
