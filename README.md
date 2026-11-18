# PlayAndPatch — Custom Calendar

This repository publishes subscription-ready iCalendar feeds based on the official PlayAndPatch calendar.

## How it works

- Fetches `https://playandpatch.com/calendar.ics?lang=en`.
- Always excludes events categorized exactly as `Sale` or `Sales` (case-insensitive).
- Publishes a default all-category feed at `calendar.ics`.
- Publishes a separate feed for every possible combination of the seven non-Sales categories (128 feeds total).
- The landing page lets visitors select categories and gives them the matching permanent subscription URL.
- GitHub Actions refreshes every feed every three hours and can also be started manually.
- New, changed, and cancelled events are reflected on the next successful refresh.

The seven selectable categories are Game Releases, Showcase, Festival, Convention, Awards, Esports, and Update. The all-category feed also retains uncategorized events, matching the original behaviour. When selecting specific categories, only events assigned to at least one selected category are included.

The job intentionally fails if expected category metadata or Sale/Sales events are missing, preventing an unexpected source-feed format from silently publishing incorrect calendars.

## Calendar URLs

- Landing page: `https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/`
- Default all-category feed: `https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/calendar.ics`

Use the landing page to select categories and copy the resulting subscription URL. Subscribe by URL in your calendar app; do not import the file if you want future updates. Calendar applications decide how often they refresh subscribed feeds.
