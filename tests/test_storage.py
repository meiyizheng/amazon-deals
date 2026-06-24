from __future__ import annotations

import json
import os
import tempfile
import unittest

from dealbot.storage import load_seen, save_seen


class LoadSeenTests(unittest.TestCase):
    def test_returns_empty_set_when_file_missing(self) -> None:
        self.assertEqual(load_seen("/nonexistent/path.json"), set())

    def test_loads_list_from_file(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(["a", "b", "c"], f)
            path = f.name
        try:
            result = load_seen(path)
            self.assertEqual(result, {"a", "b", "c"})
        finally:
            os.unlink(path)

    def test_returns_empty_set_for_corrupt_file(self) -> None:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            f.write("not json {{")
            path = f.name
        try:
            result = load_seen(path)
            self.assertEqual(result, set())
        finally:
            os.unlink(path)


class SaveSeenTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.mkdtemp()
        self.path = os.path.join(self.tmpdir, "seen.json")

    def tearDown(self) -> None:
        for name in os.listdir(self.tmpdir):
            os.unlink(os.path.join(self.tmpdir, name))
        os.rmdir(self.tmpdir)

    def test_saves_and_reloads_correctly(self) -> None:
        ids = {"abc123", "def456", "ghi789"}
        save_seen(self.path, ids)
        loaded = load_seen(self.path)
        self.assertEqual(loaded, ids)

    def test_no_temp_file_left_behind(self) -> None:
        save_seen(self.path, {"x"})
        files = os.listdir(self.tmpdir)
        tmp_files = [f for f in files if f.endswith(".tmp")]
        self.assertEqual(tmp_files, [])

    def test_keep_last_trims_oldest(self) -> None:
        # save_seen keeps the LAST keep_last items from list(seen)
        # we pass a large set and verify the output is truncated
        ids = {str(i) for i in range(100)}
        save_seen(self.path, ids, keep_last=10)
        loaded = load_seen(self.path)
        self.assertEqual(len(loaded), 10)

    def test_atomic_write_creates_target_file(self) -> None:
        self.assertFalse(os.path.exists(self.path))
        save_seen(self.path, {"deal-1"})
        self.assertTrue(os.path.exists(self.path))

    def test_creates_parent_directory(self) -> None:
        nested_path = os.path.join(self.tmpdir, "nested", "sub", "seen.json")
        save_seen(nested_path, {"deal-1"})
        self.assertTrue(os.path.exists(nested_path))
        # clean up
        import shutil
        shutil.rmtree(os.path.join(self.tmpdir, "nested"))


if __name__ == "__main__":
    unittest.main()
