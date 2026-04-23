# clockify_fill-gaps

Scans your Clockify entries for a chosen week, shows uncovered time gaps within work hours, and optionally creates filler entries for them.

**Defaults** (edit constants at the top of `main.py` to change):

| Setting | Default |
|---|---|
| Timezone | Asia/Manila |
| Work hours | 09:00 – 18:00 |
| Lunch (skipped) | 12:00 – 13:00 |
| Filler description | `[Dev Work, Reviewing code]` |

> Filler entries are **posted immediately** when you confirm with `y`.

---

## Prerequisites

- Python 3.13.7+  
- [uv](https://docs.astral.sh/uv/) (recommended) or pip  
- Clockify API key — found under your Clockify profile settings  
- Clockify workspace ID — found in your workspace URL or workspace settings

---

## Setup

**1. Install dependencies**

```bash
uv sync
```

<details>
<summary>Using pip instead</summary>

```bash
python -m pip install -e .
```

</details>

**2. Set credentials**

Create a `.env` file in the project folder:

```env
CLOCKIFY_KEY=your_api_key_here
CLOCKIFY_WORKSPACE_ID=your_workspace_id_here
```

---

## Usage

```bash
uv run main.py
```

1. Enter any date in the week you want to check (or press Enter for the current week).
2. Review the gaps printed per day:
   ```
   2026-04-20  →  10:30-11:00, 15:00-16:00
   2026-04-21  →  None
   ```
3. Answer `y` to create filler entries, or anything else to exit without changes.

> **Tip:** Run once and answer `N` first to verify gaps look correct before creating entries.

---

## Troubleshooting

| Error / symptom | Likely cause |
|---|---|
| `Please set your API key...` | `CLOCKIFY_KEY` missing or `.env` not found |
| `Please set your workspace ID...` | `CLOCKIFY_WORKSPACE_ID` missing or wrong |
| No entries found | Wrong date, wrong workspace ID, or API key lacks access |
| Wrong project on fillers | Known limitation: reuses project/task from the **first entry of that day** |
