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
    entries = []
    for t in data:
        ti = t.get("timeInterval", {})
        if ti.get("start") and ti.get("end"):
            start = parser.isoparse(ti["start"]).astimezone(LOCAL_TZ)
            end   = parser.isoparse(ti["end"]).astimezone(LOCAL_TZ)
            entries.append((start, end))
    return entries


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

    entries = get_entries(WORKSPACE_ID, user_id, start, end)
    print(f"Retrieved {len(entries)} entries for current week (local tz {LOCAL_TZ.key}).")

    by_day = group_by_local_day(entries)

    for day in sorted(by_day):
        gaps = find_gaps(by_day[day], WORK_START, WORK_END)
        gap_list = ", ".join(f"{s}-{e}" for s, e in gaps) if gaps else "None"
        print(f"{day}  →  {gap_list}")

    if not by_day:
        print("No entries found for this week. Check workspace ID or API key.")


# ====== run ======
if __name__ == "__main__":
    preview_week()