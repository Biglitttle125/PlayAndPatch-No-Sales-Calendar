# PlayAndPatch — No Sales Calendar

This repository publishes a subscription-ready iCalendar feed based on the official PlayAndPatch calendar, excluding only events whose iCalendar `CATEGORIES` value is `Sale` or `Sales`. All other categories and uncategorized events are retained.

## How it works

- Fetches `https://playandpatch.com/calendar.ics?lang=en`.
- Removes events categorized exactly as `Sale` or `Sales` (case-insensitive).
- Publishes the generated feed and landing page to GitHub Pages.
- GitHub Actions runs every three hours and can also be started manually.
- The generated calendar is deployed as a Pages artifact; it is not committed back into the source repository.

The job intentionally fails if the source feed has no category metadata or no Sale/Sales events are detected. This prevents a changed source format from silently publishing an unfiltered calendar.

## One-time GitHub Pages setup

1. Open this repository's **Settings → Pages**.
2. Under **Build and deployment**, set **Source** to **GitHub Actions**.
3. Open the **Actions** tab and select **Refresh and publish filtered PlayAndPatch calendar**.
4. Click **Run workflow** on the `main` branch.
5. Wait for the workflow to complete successfully. If it fails, open the run and inspect the **Fetch and filter calendar** or **Deploy to GitHub Pages** step.

## Calendar URLs

Once the first workflow run succeeds and Pages finishes deploying:

- Landing page: `https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/`
- Subscription feed: `https://biglitttle125.github.io/PlayAndPatch-No-Sales-Calendar/calendar.ics`

## Subscribe, don't import

In Google Calendar, choose **Other calendars → + → From URL** and paste the subscription URL. In Outlook or Apple Calendar, add a calendar by URL/subscription. Do not import the downloaded file if you want future updates: importing is a one-time snapshot, while subscribing keeps checking the feed.

Calendar applications decide how often they refresh subscribed calendars, so updates may not appear immediately even though this feed is refreshed every three hours.
