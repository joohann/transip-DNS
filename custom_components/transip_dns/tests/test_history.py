"""Unit tests for the IP history bookkeeping."""
import unittest

from _load import load

history = load().history


class RecordChangeTest(unittest.TestCase):
    def test_first_value_is_not_a_change(self):
        store = {}
        self.assertTrue(history.record_change(store, "ipv4", "1.1.1.1", "T0", 5))
        entry = history.state(store, "ipv4")
        self.assertEqual(entry["current"], "1.1.1.1")
        self.assertIsNone(entry["previous"])
        self.assertEqual(entry["changed_at"], "T0")
        self.assertEqual(entry["changes"], [])

    def test_same_value_is_ignored(self):
        store = {}
        history.record_change(store, "ipv4", "1.1.1.1", "T0", 5)
        self.assertFalse(history.record_change(store, "ipv4", "1.1.1.1", "T1", 5))
        self.assertEqual(history.state(store, "ipv4")["changed_at"], "T0")

    def test_change_moves_current_to_previous(self):
        store = {}
        history.record_change(store, "ipv4", "1.1.1.1", "T0", 5)
        self.assertTrue(history.record_change(store, "ipv4", "2.2.2.2", "T1", 5))
        entry = history.state(store, "ipv4")
        self.assertEqual(entry["current"], "2.2.2.2")
        self.assertEqual(entry["previous"], "1.1.1.1")
        self.assertEqual(entry["changed_at"], "T1")
        self.assertEqual(
            entry["changes"], [{"from": "1.1.1.1", "to": "2.2.2.2", "at": "T1"}]
        )

    def test_changes_are_newest_first_and_capped(self):
        store = {}
        for index in range(6):
            history.record_change(store, "ipv4", f"10.0.0.{index}", f"T{index}", 3)
        changes = history.state(store, "ipv4")["changes"]
        self.assertEqual(len(changes), 3)
        self.assertEqual(changes[0]["to"], "10.0.0.5")
        self.assertEqual(changes[-1]["to"], "10.0.0.3")

    def test_none_is_ignored(self):
        store = {}
        history.record_change(store, "ipv6", "2001:db8::1", "T0", 5)
        self.assertFalse(history.record_change(store, "ipv6", None, "T1", 5))
        self.assertEqual(history.state(store, "ipv6")["current"], "2001:db8::1")

    def test_state_of_unknown_key_is_empty(self):
        self.assertEqual(
            history.state({}, "ipv4"),
            {"current": None, "previous": None, "changed_at": None, "changes": []},
        )

    def test_trim_lowers_existing_logs(self):
        store = {}
        for index in range(6):
            history.record_change(store, "ipv4", f"10.0.0.{index}", f"T{index}", 10)
        history.trim(store, 2)
        self.assertEqual(len(history.state(store, "ipv4")["changes"]), 2)

    def test_state_returns_a_copy(self):
        store = {}
        history.record_change(store, "ipv4", "1.1.1.1", "T0", 5)
        history.record_change(store, "ipv4", "2.2.2.2", "T1", 5)
        snapshot = history.state(store, "ipv4")
        snapshot["changes"].clear()
        self.assertEqual(len(history.state(store, "ipv4")["changes"]), 1)


if __name__ == "__main__":
    unittest.main()
