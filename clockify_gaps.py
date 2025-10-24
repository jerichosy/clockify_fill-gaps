#!/usr/bin/env python3
"""
Clockify Weekly Gap Preview (local‑time corrected, read‑only)

Requirements:
  pip install requests python-dateutil

Usage:
  export CLOCKIFY_KEY=your_api_key
  python clockify_weekly_gaps.py
"""

import os
import requests
import datetime
from dateutil import parser
from zoneinfo import ZoneInfo   # Python 3.9+

# ====== configuration ======
API_KEY = os.getenv("CLOCKIFY_KEY")
if not API_KEY:
    raise SystemExit("Please set your API key in CLOCKIFY_KEY environment variable.")

WORKSPACE_ID = "65fb8f6f9c0c297dc5efdef5"  # <-- put your workspace ID here
LOCAL_TZ = ZoneInfo("Asia/Manila")         # your actual timezone
WORK_START = 8 * 60   # 08:00
WORK_END   = 17 * 60  # 17:00

HEADERS = {"x-api-key": API_KEY}


# ====== helper functions ======
def pad(n: int) -> str:
    return f"{n:02d}"


def to_minutes(dt: datetime.datetime) -> int:
    """minute‑of‑day for a localized datetime"""
    return dt.hour * 60 + dt.minute


def to_hhmm(m: int) -> str:
    return f"{pad(m // 60)}:{pad(m % 60)}"


def find_gaps(entries, start_m: int, end_m: int):
    """Return list of (start,end) hh:mm gaps inside work hours for one day."""
    spans = sorted((to_minutes(s), to_minutes(e)) for s, e in entries)
    merged = []
    for s, e in spans:
        if not merged or s > merged[-1][1]:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)

    gaps, cur = [], start_m
    for s, e in merged:
        if cur < s:
            gaps.append((cur, min(s, end_m)))
        cur = max(cur, e)
        if cur >= end_m:
            break
    if cur < end_m:
        gaps.append((cur, end_m))
    return [(to_hhmm(a), to_hhmm(b)) for a, b in gaps if b > a]


def get_user_info():
    """Return current user info identified by the API key."""
    url = "https://api.clockify.me/api/v1/user"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return res.json()


def get_entries(workspace_id, user_id, start_dt, end_dt):
    """GET all time entries for the user within a date range (UTC)."""
    # ensure pure UTC and single 'Z'
    start_utc = start_dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    end_utc   = end_dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    url = (
        f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/user/{user_id}/time-entries"
        f"?start={start_utc}&end={end_utc}"
    )
    print(f"Fetching entries for {start_dt.date()}—{end_dt.date()} …")
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    raw_data = r.json()          # keep the full JSON
    entries = []
    for t in data:
        ti = t.get("timeInterval", {})
        if ti.get("start") and ti.get("end"):
            start = parser.isoparse(ti["start"]).astimezone(LOCAL_TZ)
            end   = parser.isoparse(ti["end"]).astimezone(LOCAL_TZ)
            entries.append((start, end))
    return entries, raw_data


def post_time_entry(workspace_id, project_id, task_id, description,
                    start_dt, end_dt, billable=True):
    """POST one new time entry to Clockify."""
    body = {
        "start": start_dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "end":   end_dt.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "billable": billable,
        "projectId": project_id,
        "taskId": task_id,
        "description": description,
        # optional flags:
        "type": "REGULAR",
    }

    url = f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/time-entries"
    res = requests.post(url, headers=HEADERS, json=body)
    if res.status_code not in (200,201):
        print("⚠️  POST failed:", res.status_code, res.text)
    return res


def group_by_local_day(entries):
    """Group entries by local day."""
    grouped = {}
    for s_local, e_local in entries:
        grouped.setdefault(s_local.date(), []).append((s_local, e_local))
    return grouped


# ====== main logic ======
def preview_week():
    user = get_user_info()
    user_id = user["id"]
    print(f"Logged in as {user.get('name') or user.get('email')}  (user_id={user_id})")

    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    start = datetime.datetime.combine(monday, datetime.time(0, 0, tzinfo=datetime.timezone.utc))
    end = start + datetime.timedelta(days=7)

    entries, raw_data = get_entries(WORKSPACE_ID, user_id, start, end)
    print(f"Retrieved {len(entries)} entries for current week (local tz {LOCAL_TZ.key}).")

    by_day = group_by_local_day(entries)

    for day in sorted(by_day):
        gaps = find_gaps(by_day[day], WORK_START, WORK_END)
        gap_list = ", ".join(f"{s}-{e}" for s, e in gaps) if gaps else "None"
        print(f"{day}  →  {gap_list}")

    if not by_day:
        print("No entries found for this week. Check workspace ID or API key.")

    # after printing gaps
    confirm = input("\nCreate filler entries for shown gaps? (y/N): ").strip().lower()
    if confirm != "y":
        print("No entries created.");  return

    # create one filler entry per gap, reusing first meeting's project/task
    for day in sorted(by_day):
        if not by_day[day]: continue
        # reuse project/task info from first meeting JSON in this day
        first_raw = next((t for t in raw_data if parser.isoparse(t["timeInterval"]["start"]).astimezone(LOCAL_TZ).date()==day), None)
        if not first_raw:
            continue
        project = first_raw.get("projectId") or first_raw.get("project",{}).get("id")
        task    = first_raw.get("taskId") or first_raw.get("task",{}).get("id")
        billable = bool(first_raw.get("billable", True))
        desc = "[Auto‑fill Dev Work]"
        for s,e in find_gaps(by_day[day], WORK_START, WORK_END):
            # build local datetimes for the same day
            s_dt = datetime.datetime.combine(day, datetime.time.fromisoformat(s), tzinfo=LOCAL_TZ)
            e_dt = datetime.datetime.combine(day, datetime.time.fromisoformat(e), tzinfo=LOCAL_TZ)
            print(f"→ Creating {desc} {s}-{e} ({day})")
            # uncomment next line when ready:
            # post_time_entry(WORKSPACE_ID, project, task, desc, s_dt, e_dt, billable)


# ====== run ======
if __name__ == "__main__":
    preview_week()