import unittest
import os
from tempfile import TemporaryDirectory
from persistence.csv_persistence import CSVPersistence  # adjust import path

class DummyStruct:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class TestCSVPersistence(unittest.TestCase):
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.file_path = os.path.join(self.temp_dir.name, "test.csv")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_write_single_object_appends_and_writes_header(self):
        history_writer = CSVPersistence(self.file_path, append_mode=True)
        pos1 = DummyStruct(symbol="BTCUSDT", entry=100.0, type="long")
        history_writer.write(pos1)

        with open(self.file_path, "r", encoding="utf-8") as f:
            actual_csv = f.read()

        expected_csv = (
            "symbol,entry,type\n"
            "BTCUSDT,100.0,long\n"
        )
        self.assertEqual(actual_csv, expected_csv)

    def test_write_append_when_append_mode_true(self):
        history_writer = CSVPersistence(self.file_path, append_mode=True)
        pos1 = DummyStruct(symbol="BTCUSDT", entry=100.0, type="long")
        history_writer.write(pos1)

        pos2 = DummyStruct(symbol="ETHUSDT", entry=200.0, type="short")
        history_writer.write(pos2)

        with open(self.file_path, "r", encoding="utf-8") as f:
            actual_csv = f.read()

        expected_csv = (
            "symbol,entry,type\n"
            "BTCUSDT,100.0,long\n"
            "ETHUSDT,200.0,short\n"
        )
        self.assertEqual(actual_csv, expected_csv)

    def test_write_list_append_when_append_mode_true(self):
        current_positions = CSVPersistence(self.file_path, append_mode=True)
        
        pos1 = DummyStruct(symbol="BTCUSDT", entry=100.0, type="long")
        pos2 = DummyStruct(symbol="ETHUSDT", entry=200.0, type="short")
        current_positions.write([pos1, pos2])

        with open(self.file_path, "r", encoding="utf-8") as f:
            actual_csv = f.read()

        expected_csv = (
            "symbol,entry,type\n"
            "BTCUSDT,100.0,long\n"
            "ETHUSDT,200.0,short\n"
        )
        self.assertEqual(actual_csv, expected_csv)

        pos3 = DummyStruct(symbol="BNBUSDT", entry=300.0, type="long")
        pos4 = DummyStruct(symbol="XRPUSDT", entry=400.0, type="short")
        current_positions.write([pos3, pos4])

        with open(self.file_path, "r", encoding="utf-8") as f:
            actual_csv = f.read()

        expected_csv = (
            "symbol,entry,type\n"
            "BTCUSDT,100.0,long\n"
            "ETHUSDT,200.0,short\n"
            "BNBUSDT,300.0,long\n"
            "XRPUSDT,400.0,short\n"
        )
        self.assertEqual(actual_csv, expected_csv)

    def test_write_dict_object(self):
        writer = CSVPersistence(self.file_path, append_mode=True)
        obj1 = {"symbol": "XRPUSDT", "entry": 0.5, "type": "long"}
        obj2 = {"symbol": "BTCUSDT", "entry": 110000, "type": "short"}
        writer.write([obj1, obj2])

        with open(self.file_path, "r", encoding="utf-8") as f:
            actual_csv = f.read()

        expected_csv = (
            "symbol,entry,type\n"
            "XRPUSDT,0.5,long\n"
            "BTCUSDT,110000,short\n"
        )
        self.assertEqual(actual_csv, expected_csv)

    def test_write_overwrites_when_append_mode_false(self):
        current_positions = CSVPersistence(self.file_path, append_mode=False)
        obj1 = DummyStruct(symbol="BTCUSDT", entry=100.0, type="long")
        current_positions.write(obj1)

        obj2 = DummyStruct(symbol="ETHUSDT", entry=200.0, type="short")
        current_positions.write(obj2)

        with open(self.file_path, "r", encoding="utf-8") as f:
            actual_csv = f.read()

        expected_csv = (
            "symbol,entry,type\n"
            "ETHUSDT,200.0,short\n"
        )
        self.assertEqual(actual_csv, expected_csv)

    def test_write_list_overwrites_when_append_mode_false(self):
        current_positions = CSVPersistence(self.file_path, append_mode=False)
        
        pos1 = DummyStruct(symbol="BTCUSDT", entry=100.0, type="long")
        pos2 = DummyStruct(symbol="ETHUSDT", entry=200.0, type="short")
        current_positions.write([pos1, pos2])

        with open(self.file_path, "r", encoding="utf-8") as f:
            actual_csv = f.read()

        expected_csv = (
            "symbol,entry,type\n"
            "BTCUSDT,100.0,long\n"
            "ETHUSDT,200.0,short\n"
        )
        self.assertEqual(actual_csv, expected_csv)

        pos3 = DummyStruct(symbol="BNBUSDT", entry=300.0, type="long")
        pos4 = DummyStruct(symbol="XRPUSDT", entry=400.0, type="short")
        current_positions.write([pos3, pos4])

        with open(self.file_path, "r", encoding="utf-8") as f:
            actual_csv = f.read()

        expected_csv = (
            "symbol,entry,type\n"
            "BNBUSDT,300.0,long\n"
            "XRPUSDT,400.0,short\n"
        )
        self.assertEqual(actual_csv, expected_csv)

    def test_write_empty_list_does_nothing(self):
        writer = CSVPersistence(self.file_path)
        writer.write([])

        self.assertFalse(os.path.exists(self.file_path))