#!/usr/bin/env python3
"""
Clockify Weekly Gap Preview (read‑only)

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

# ====== configuration ======
API_KEY = os.getenv("CLOCKIFY_KEY")
if not API_KEY:
    raise SystemExit("Please set your API key in CLOCKIFY_KEY environment variable.")

WORKSPACE_ID = "65fb8f6f9c0c297dc5efdef5"  # <-- put your workspace ID here
WORK_START = 8 * 60   # 08:00
WORK_END   = 17 * 60  # 17:00

HEADERS = {"x-api-key": API_KEY}

# ====== helper functions ======
def pad(n: int) -> str:
    return f"{n:02d}"

def to_minutes(dt: datetime.datetime) -> int:
    return dt.hour * 60 + dt.minute

def to_hhmm(m: int) -> str:
    return f"{pad(m // 60)}:{pad(m % 60)}"

def find_gaps(entries, start_m: int, end_m: int):
    """Return a list of gaps (start,end) within working hours for a single day."""
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
    """GET all time entries for the user within a date range."""
    url = (
        f"https://api.clockify.me/api/v1/workspaces/{workspace_id}/user/{user_id}/time-entries"
        f"?start={start_dt.isoformat()}Z&end={end_dt.isoformat()}Z"
    )
    print(f"Fetching entries for {start_dt.date()}—{end_dt.date()} …")
    r = requests.get(url, headers=HEADERS)
    r.raise_for_status()
    data = r.json()
    entries = []
    for t in data:
        ti = t.get("timeInterval", {})
        if ti.get("start") and ti.get("end"):
            start = parser.isoparse(ti["start"])
            end = parser.isoparse(ti["end"])
            entries.append((start, end))
    return entries

def group_by_local_day(entries):
    grouped = {}
    for start, end in entries:
        k = start.astimezone().date()
        grouped.setdefault(k, []).append((start, end))
    return grouped

# ====== main logic ======
def preview_week():
    user = get_user_info()
    user_id = user["id"]
    print(f"Logged in as {user.get('name') or user.get('email')}  (user_id={user_id})")

    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday())
    start = datetime.datetime.combine(monday, datetime.time(0, 0))
    end = start + datetime.timedelta(days=7)

    entries = get_entries(WORKSPACE_ID, user_id, start, end)
    print(f"Retrieved {len(entries)} entries for current week.")

    grouped = group_by_local_day(entries)

    for day in sorted(grouped):
        gaps = find_gaps(grouped[day], WORK_START, WORK_END)
        gap_list = ", ".join(f"{s}-{e}" for s, e in gaps) if gaps else "None"
        print(f"{day}  →  {gap_list}")

    if not grouped:
        print("No entries found for this week. Check your workspace ID or API key.")

# ====== run ======
if __name__ == "__main__":
    preview_week()