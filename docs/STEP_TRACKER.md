# Step Tracker

This minimal agent lets individuals privately track weekly steps in their browser using `localStorage`.

Files:
- [tracker/index.html](tracker/index.html) — UI to set a weekly goal, add daily steps, view weekly progress, export CSV, and reset data.
- [tracker/app.js](tracker/app.js) — Logic: saves per-user state to `localStorage` under `step-tracker:<name>`.
- [tracker/style.css](tracker/style.css) — Simple styles.
- [data/step_counts.csv](data/step_counts.csv) — CSV template for bulk import/export.

Usage:
- Open [tracker/index.html](tracker/index.html) in a browser.
- Enter your name and weekly goal, click `Save`.
- Add daily steps (date and steps) and click `Add` to accumulate entries.
- The dashboard shows weekly total and percent toward the goal (Mon–Sun week).
- Click `Export CSV` to download your entries (private to your browser).

Privacy:
- All data is stored locally in the browser. There is no server or remote storage.
