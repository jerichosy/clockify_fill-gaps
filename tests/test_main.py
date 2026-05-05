import contextlib
import datetime
import importlib
import io
import os
import unittest
from unittest import mock

with mock.patch.dict(
    os.environ,
    {"CLOCKIFY_KEY": "test-key", "CLOCKIFY_WORKSPACE_ID": "workspace-id"},
    clear=False,
):
    import main as main_module

    main = importlib.reload(main_module)


class TestFindGaps(unittest.TestCase):
    def test_empty_entries_shows_work_hours_excluding_lunch(self):
        gaps = main.find_gaps([], main.WORK_START, main.WORK_END)

        self.assertEqual(gaps, [("09:00", "12:00"), ("13:00", "18:00")])

    def test_overlaps_merge_with_lunch(self):
        day = datetime.date(2024, 2, 5)
        entries = [
            (
                datetime.datetime.combine(day, datetime.time(9, 0), tzinfo=main.LOCAL_TZ),
                datetime.datetime.combine(day, datetime.time(11, 30), tzinfo=main.LOCAL_TZ),
            ),
            (
                datetime.datetime.combine(day, datetime.time(11, 0), tzinfo=main.LOCAL_TZ),
                datetime.datetime.combine(day, datetime.time(12, 0), tzinfo=main.LOCAL_TZ),
            ),
            (
                datetime.datetime.combine(day, datetime.time(15, 0), tzinfo=main.LOCAL_TZ),
                datetime.datetime.combine(day, datetime.time(16, 0), tzinfo=main.LOCAL_TZ),
            ),
        ]

        gaps = main.find_gaps(entries, main.WORK_START, main.WORK_END)

        self.assertEqual(gaps, [("13:00", "15:00"), ("16:00", "18:00")])


class TestGroupByLocalDay(unittest.TestCase):
    def test_groups_entries_by_start_date(self):
        day_one = datetime.date(2024, 3, 4)
        day_two = datetime.date(2024, 3, 5)
        entries = [
            (
                datetime.datetime.combine(day_one, datetime.time(9, 0), tzinfo=main.LOCAL_TZ),
                datetime.datetime.combine(day_one, datetime.time(10, 0), tzinfo=main.LOCAL_TZ),
            ),
            (
                datetime.datetime.combine(day_two, datetime.time(14, 0), tzinfo=main.LOCAL_TZ),
                datetime.datetime.combine(day_two, datetime.time(15, 0), tzinfo=main.LOCAL_TZ),
            ),
        ]

        grouped = main.group_by_local_day(entries)

        self.assertEqual(set(grouped.keys()), {day_one, day_two})
        self.assertEqual(grouped[day_one], [entries[0]])
        self.assertEqual(grouped[day_two], [entries[1]])


class TestPreviewWeek(unittest.TestCase):
    @mock.patch("main.post_time_entry")
    @mock.patch("main.get_entries")
    @mock.patch("main.get_user_info")
    @mock.patch("builtins.input")
    def test_prints_gaps_for_selected_week(
        self, mock_input, mock_get_user_info, mock_get_entries, mock_post_time_entry
    ):
        selected_date = "2024-04-10"
        decline_confirmation = "n"
        mock_input.side_effect = [selected_date, decline_confirmation]
        mock_get_user_info.return_value = {"id": "user-123", "name": "Test User"}

        monday = datetime.date(2024, 4, 8)
        tuesday = monday + datetime.timedelta(days=1)
        entries = [
            (
                datetime.datetime.combine(monday, datetime.time(9, 0), tzinfo=main.LOCAL_TZ),
                datetime.datetime.combine(monday, datetime.time(10, 0), tzinfo=main.LOCAL_TZ),
            ),
            (
                datetime.datetime.combine(tuesday, datetime.time(9, 0), tzinfo=main.LOCAL_TZ),
                datetime.datetime.combine(tuesday, datetime.time(18, 0), tzinfo=main.LOCAL_TZ),
            ),
        ]
        raw_data = []
        mock_get_entries.return_value = (entries, raw_data)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.preview_week()

        text = output.getvalue()
        self.assertIn("Previewing week of 2024-04-08 → 2024-04-14", text)
        self.assertIn(
            f"Retrieved 2 entries for current week (local tz {main.LOCAL_TZ.key}).",
            text,
        )
        self.assertIn("2024-04-08  →  10:00-12:00, 13:00-18:00", text)
        self.assertIn("2024-04-09  →  None", text)
        self.assertIn("No entries created.", text)
        mock_post_time_entry.assert_not_called()

        _, _, start_dt, end_dt = mock_get_entries.call_args[0]
        self.assertEqual(start_dt.tzinfo, datetime.timezone.utc)
        self.assertEqual(start_dt.date(), monday)
        self.assertEqual(end_dt, start_dt + datetime.timedelta(days=7))

    @mock.patch("main.post_time_entry")
    @mock.patch("main.get_entries")
    @mock.patch("main.get_user_info")
    @mock.patch("builtins.input")
    def test_creates_filler_entries_when_confirmed(
        self, mock_input, mock_get_user_info, mock_get_entries, mock_post_time_entry
    ):
        selected_date = "2024-04-10"
        confirm_creation = "y"
        mock_input.side_effect = [selected_date, confirm_creation]
        mock_get_user_info.return_value = {"id": "user-456", "email": "tester@example.com"}

        monday = datetime.date(2024, 4, 8)
        start_local = datetime.datetime.combine(monday, datetime.time(9, 0), tzinfo=main.LOCAL_TZ)
        end_local = datetime.datetime.combine(monday, datetime.time(10, 0), tzinfo=main.LOCAL_TZ)
        entries = [(start_local, end_local)]
        start_utc = start_local.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        end_utc = end_local.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        raw_data = [
            {
                "timeInterval": {"start": start_utc, "end": end_utc},
                "projectId": "project-1",
                "taskId": "task-1",
                "billable": False,
            }
        ]
        mock_get_entries.return_value = (entries, raw_data)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main.preview_week()

        self.assertEqual(mock_post_time_entry.call_count, 2)
        first_call, second_call = mock_post_time_entry.call_args_list
        self.assertEqual(
            first_call.args,
            (
                main.WORKSPACE_ID,
                "project-1",
                "task-1",
                main.ENTRY_DESC,
                datetime.datetime.combine(monday, datetime.time(10, 0), tzinfo=main.LOCAL_TZ),
                datetime.datetime.combine(monday, datetime.time(12, 0), tzinfo=main.LOCAL_TZ),
                False,
            ),
        )
        self.assertEqual(
            second_call.args,
            (
                main.WORKSPACE_ID,
                "project-1",
                "task-1",
                main.ENTRY_DESC,
                datetime.datetime.combine(monday, datetime.time(13, 0), tzinfo=main.LOCAL_TZ),
                datetime.datetime.combine(monday, datetime.time(18, 0), tzinfo=main.LOCAL_TZ),
                False,
            ),
        )


if __name__ == "__main__":
    unittest.main()
