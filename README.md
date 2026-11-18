# PlayAndPatch — No Sales Calendar

This repository publishes a subscription-ready iCalendar feed based on the official PlayAndPatch calendar, excluding only events whose iCalendar `CATEGORIES` value is `Sale` or `Sales`. All other categories and uncategorized events are retained.

## How it works

- Fetches `https://playandpatch.com/calendar.ics?lang=en`.
- Removes events categorized exactly as `Sale` or `Sales` (case-insensitive).
- Publishes the result to `docs/calendar.ics`.
- GitHub Actions runs every three hours and can also be started manually.
- The generated feed is committed only when its contents change.

The job intentionally fails if the source feed has no category metadata or no Sale/Sales events are detected. This prevents a changed source format from silently publishing an unfiltered calendar.

## Enable GitHub Pages

1. Open the repository's **Settings → Pages**.
2. Under **Build and deployment**, choose **Deploy from a branch**.
3. Select branch **main** and folder **/docs**, then save.
4. Open **Actions**, select **Refresh filtered PlayAndPatch calendar**, and click **Run workflow** once.
5. Wait for the workflow to finish successfully and for GitHub Pages to publish.

Your subscription URL will be:

`https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/calendar.ics`

The landing page is:

`https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/`

## Subscribe, don't import

In Google Calendar, choose **Other calendars → + → From URL** and paste the subscription URL. In Outlook or Apple Calendar, add a calendar by URL/subscription. Do not import the downloaded file if you want future updates: importing is a one-time snapshot, while subscribing keeps checking the feed.

Calendar applications decide how often they refresh subscribed calendars, so updates may not appear immediately even though this feed is refreshed every three hours.
