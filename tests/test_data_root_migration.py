# -*- coding: utf-8 -*-
"""El directorio de datos cambia de nombre con la aplicación; la migración lo traslada."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from videodrome import distribution


class DataRootMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.environ = {"LOCALAPPDATA": str(self.base)} if os.name == "nt" else {}

    def _roots(self):
        with mock.patch.object(distribution, "_base", return_value=self.base):
            return distribution.user_data_root(self.environ), distribution.legacy_user_data_root(self.environ)

    def test_the_data_root_uses_the_new_name(self):
        new, old = self._roots()
        self.assertIn("Videodrome", new.parts)
        self.assertIn("Peach", old.parts)
        self.assertNotEqual(new, old)

    def test_the_legacy_directory_is_moved_when_the_new_one_is_absent(self):
        new, old = self._roots()
        old.mkdir(parents=True)
        (old / "config.toml").write_text("x", encoding="utf-8")
        with mock.patch.object(distribution, "_base", return_value=self.base):
            result, moved = distribution.migrate_legacy_data_root(self.environ)
        self.assertEqual(result, new)
        self.assertEqual(moved, old)
        self.assertTrue((new / "config.toml").is_file())
        self.assertFalse(old.exists())

    def test_nothing_moves_when_the_new_directory_already_exists(self):
        new, old = self._roots()
        new.mkdir(parents=True)
        old.mkdir(parents=True)
        (old / "config.toml").write_text("viejo", encoding="utf-8")
        (new / "config.toml").write_text("nuevo", encoding="utf-8")
        with mock.patch.object(distribution, "_base", return_value=self.base):
            result, moved = distribution.migrate_legacy_data_root(self.environ)
        self.assertIsNone(moved)
        self.assertEqual((new / "config.toml").read_text(encoding="utf-8"), "nuevo")
        self.assertEqual((old / "config.toml").read_text(encoding="utf-8"), "viejo")

    def test_migrating_without_a_legacy_directory_does_nothing(self):
        new, _old = self._roots()
        with mock.patch.object(distribution, "_base", return_value=self.base):
            result, moved = distribution.migrate_legacy_data_root(self.environ)
        self.assertEqual(result, new)
        self.assertIsNone(moved)
        self.assertFalse(new.exists())
