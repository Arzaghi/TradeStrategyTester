import unittest
import tempfile
from pathlib import Path

from config import Config, ConfigSection, config


class TestConfig(unittest.TestCase):
    def setUp(self):
        # Create a temporary INI file for testing
        self.temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".ini")
        self.temp_file.write(b"""
            [general]
            name = HeLLoWoRLd
            version = 1.2.3

            [database]
            HOST = LOCALHOST
            PORT = 5432

            [mixed]
            Key1 = VALUE
            Key2 = MiXeDCase
            """
        
        )
        self.temp_file.close()

        Config._config_file = Path(self.temp_file.name)
        config.reload()

    def tearDown(self):
        Path(self.temp_file.name).unlink(missing_ok=True)

    def test_lowercase_via_attr(self):
        self.assertEqual(config.general.name, "helloworld")
        self.assertEqual(config.general.version, "1.2.3")  # already lowercase digits
        self.assertEqual(config.database.host, "localhost")
        self.assertEqual(config.database.port, "5432")
        self.assertEqual(config.mixed.key1, "value")
        self.assertEqual(config.mixed.key2, "mixedcase")

    def test_via_section_get(self):
        self.assertEqual(config.database.get("host"), "localhost")
        self.assertEqual(config.database.get("port"), "5432")
        self.assertEqual(config.mixed.get("key1"), "value")
        self.assertEqual(config.mixed.get("key2"), "mixedcase")

    def test_via_config_get(self):
        self.assertEqual(config.get("general", "name"), "helloworld")
        self.assertEqual(config.get("general", "version"), "1.2.3")
        self.assertEqual(config.get("database", "host"), "localhost")
        self.assertEqual(config.get("mixed", "key2"), "mixedcase")

    def test_defaults(self):
        self.assertEqual(config.get("general", "missing", default="FALLBACK"), "fallback")
        self.assertEqual(config.general.get("missing", default="FALLBACK"), "fallback")
        self.assertEqual(config.get("nosuch", "key", default="FALLBACK"), "fallback")
        self.assertEqual(config.get("general", "missing", default=123), 123)
        self.assertEqual(config.general.get("missing", default=123), 123)
        self.assertIsNone(config.general.get("missing"))

    def test_missing_behavior(self):
        self.assertIsNone(config.nosuchsection)
        self.assertIsNone(config.general.missingkey)
        self.assertIsInstance(config.get("database"), ConfigSection)

    def test_get_value_existing(self):
        self.assertEqual(config.get_value("general.name", "fallback"), "helloworld")
        self.assertEqual(config.get_value("general.version", "fallback"), "1.2.3")
        self.assertEqual(config.get_value("database.host", "fallback"), "localhost")
        self.assertEqual(config.get_value("database.port", "fallback"), "5432")
        self.assertEqual(config.get_value("mixed.key1", "fallback"), "value")
        self.assertEqual(config.get_value("mixed.key2", "fallback"), "mixedcase")

        self.assertEqual(config.get_value("general.missing", "FALLBACK"), "fallback")
        self.assertEqual(config.get_value("database.missing", "FALLBACK"), "fallback")

        self.assertEqual(config.get_value("nosuch.key", "FALLBACK"), "fallback")

        # no dot in path → return default
        self.assertEqual(config.get_value("invalidpath", "FALLBACK"), "fallback")
        self.assertEqual(config.get_value("", "FALLBACK"), "fallback")
