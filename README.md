# clockify_fill-gaps

Simple tool to help you fill missing work-time gaps in your weekly Clockify timesheet.

This is for people who are not developers but can follow technical setup steps.

## What this tool does

If your company requires a full 9:00 AM to 6:00 PM timesheet, this script can:

1. Read your Clockify entries for a selected week
2. Show time gaps between your existing entries
3. Optionally create "filler" entries for those gaps

It uses your existing entries in that day as reference for project/task/billable settings.

---

## Important behavior (read first)

- Timezone is set to **Asia/Manila** by default.
- Work hours are set to **09:00 to 18:00**.
- Lunch break **12:00 to 13:00** is treated as busy, so no filler is created there.
- Filler description is currently: `[Dev Work, Reviewing code]`
- If you confirm creation, entries are posted to Clockify immediately.

---

## Requirements

- Python **3.13.7+**
- Clockify API key
- Clockify workspace ID

## 1) Get your Clockify API key

In Clockify:

1. Open your profile/settings
2. Find your API key
3. Copy it

## 2) Get your Workspace ID

You can get this from your Clockify workspace URL or workspace settings.

---

## Setup

From the project folder, install dependencies:

```bash
python -m pip install -e .
```

Set required environment variables (Linux/macOS):

```bash
export CLOCKIFY_KEY="your_api_key_here"
export CLOCKIFY_WORKSPACE_ID="your_workspace_id_here"
```

Or create a `.env` file in the same folder as `main.py`:

```env
CLOCKIFY_KEY=your_api_key_here
CLOCKIFY_WORKSPACE_ID=your_workspace_id_here
```

---

## Run the tool

```bash
python main.py
```

You will be asked:

`Enter any date within the week to preview (blank for today):`

- Press Enter for current week
- Or type a date like `2026-04-20` (any day in the week you want)

The script will then print daily gaps for that week.

Example:

```text
2026-04-20  →  10:30-11:00, 15:00-16:00
2026-04-21  →  None
```

Then it asks:

`Create filler entries for shown gaps? (y/N):`

- Type `y` to create entries
- Anything else = no changes

---

## Recommended safe usage

1. Run once and **do not** create entries yet (answer `N`)
2. Check if the detected gaps are correct
3. Run again and answer `y` only when sure

---

## Troubleshooting

### "Please set your API key..."
Your `CLOCKIFY_KEY` is missing or not loaded.

### "Please set your workspace ID..."
Your `CLOCKIFY_WORKSPACE_ID` is missing or incorrect.

### No entries found for the week
- Wrong date/week selected
- Wrong workspace ID
- API key does not have access to that workspace

### Wrong project/task used in fillers
Known limitation: it reuses project/task from the **first entry of that day**.

---

## Customize defaults (optional)

Open `main.py` and adjust constants near the top:

- `LOCAL_TZ`
- `WORK_START` / `WORK_END`
- `LUNCH_START` / `LUNCH_END`
- `ENTRY_DESC`

---

## Notes

- This script uses Clockify API v1.
- It only handles entries that have both start and end times.
