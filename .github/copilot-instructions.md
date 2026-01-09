# Copilot Instructions for clockify_fill-gaps

- **Purpose**: Single-file CLI to preview weekly Clockify gaps (local-time corrected) and optionally auto-create filler entries; entry point is [main.py](../main.py).
- **Runtime/deps**: Targets Python 3.13.7+ ([pyproject.toml](../pyproject.toml)); installs `requests`, `python-dateutil`, `python-dotenv`, and `tzdata` (needed on Windows for `ZoneInfo`). Use `python -m pip install -e .` to pull dependencies.
- **Secrets/config**: Requires env vars `CLOCKIFY_KEY` and `CLOCKIFY_WORKSPACE_ID`; missing values abort early in [main.py](../main.py). `.env` is loaded automatically via `python-dotenv`.
- **Timezone & work window**: All API timestamps are converted to `ZoneInfo("Asia/Manila")`; adjust `LOCAL_TZ` to change region. Workday limits `WORK_START/WORK_END` default to 09:00–18:00; lunch `LUNCH_START/LUNCH_END` (12:00–13:00) is treated as busy so fillers never cover it ([main.py](../main.py)).
- **Gap detection**: `find_gaps()` converts localized entries to minute-of-day, merges overlaps, injects lunch as a blocked span, and returns `HH:MM` gaps within the work window ([main.py](../main.py)). Keep spans sorted and minutes-based if you change rules.
- **API flow**: `preview_week()` → `get_user_info()` (Clockify v1 `user`) → `get_entries()` (v1 `time-entries` GET over UTC range) → localize → `group_by_local_day()` → `find_gaps()` per day ([main.py](../main.py)). Headers always include `x-api-key`.
- **Week selection**: Prompt accepts any `YYYY-MM-DD`; blank defaults to today; invalid input falls back to today with a notice. The script computes the Monday–Sunday window containing that date ([main.py](../main.py)).
- **Preview output**: Prints gaps per day as `HH:MM-HH:MM`, or `None` when fully covered ([main.py](../main.py)).
- **Posting behavior**: After preview, prompt `Create filler entries... (y/N)`. On `y`, picks the first entry of each local day to reuse `projectId`, `taskId`, and `billable`; posts one filler per gap with `ENTRY_DESC` ([main.py](../main.py)).
- **Safety**: `post_time_entry()` is live (Clockify v1 POST); fillers are created immediately. Comment out the call inside `preview_week()` if you need a dry-run. Warn on non-200/201 responses ([main.py](../main.py)).
- **Request formatting**: All outbound timestamps are forced to UTC with a trailing `Z` (`%Y-%m-%dT%H:%M:%SZ`); inbound GET params use `.000Z` and payloads use the same format ([main.py](../main.py)).
- **Defaults to reuse**: `ENTRY_DESC` is the filler description template; adjust constants near the top for work hours, lunch, and timezone ([main.py](../main.py)).
- **Running locally**: Typical flow—export `CLOCKIFY_KEY`/`CLOCKIFY_WORKSPACE_ID` (or use `.env`), run `python main.py`, choose a date, review gaps, then confirm posting.
- **Extending/patching**: If you need per-day project selection, change the `first_raw` lookup in `preview_week()`; keep the `raw_data` list intact for richer metadata. For new gap rules (breaks, holidays), inject spans before the merge inside `find_gaps()`.
- **Diagnostics**: Network calls use `raise_for_status()` on GET; POST prints warnings only. Add retries/logging around `requests` if running unattended.
