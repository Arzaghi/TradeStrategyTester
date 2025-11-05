import unittest
import tempfile
import os
import time
import shutil
from persistence import CSVLogger, PositionsHistoryLogger, CurrentPositionsLogger
from models import Position

class TestCSVLoggerFolderCreation(unittest.TestCase):
    def setUp(self):
        # Create a temp directory and then delete it to simulate missing path
        self.temp_dir = tempfile.mkdtemp()
        shutil.rmtree(self.temp_dir)  # Remove it so logger must recreate it
        self.filename = os.path.join(self.temp_dir, "log.csv")
        self.fieldnames = ["symbol", "entry", "exit"]

    def tearDown(self):
        # Clean up if the logger recreated the folder
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_logger_creates_missing_folder(self):
        class Position:
            symbol = "BTCUSDT"
            entry = 100.0
            exit = 110.0
            morefields = "should not put it in log"

        logger = CSVLogger(filename=self.filename, fieldnames=self.fieldnames)
        logger.write(Position())

        # Assert folder and file were created
        self.assertTrue(os.path.isdir(self.temp_dir))
        self.assertTrue(os.path.isfile(self.filename))

        # Assert file content
        with open(self.filename, "r") as f:
            content = f.read().strip()
        expected = "symbol,entry,exit\nBTCUSDT,100.0,110.0"
        self.assertEqual(content, expected)

class TestCSVLogger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.filename = os.path.join(self.temp_dir.name, "test_log.csv")
        self.fieldnames = ["symbol", "entry_price", "exit_price", "profit"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_csv_as_string(self):
        with open(self.filename, "r", encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")  # Normalize line endings

    def test_single_row(self):
        class Obj: pass
        obj = Obj()
        obj.symbol = "AAPL"
        obj.entry_price = 150.0
        obj.exit_price = 155.5
        obj.profit = 5.5

        logger = CSVLogger(filename=self.filename, fieldnames=self.fieldnames)
        logger.write(obj)

        expected = (
            "symbol,entry_price,exit_price,profit\n"
            "AAPL,150.0,155.5,5.5\n"
        )
        self.assertEqual(self.read_csv_as_string(), expected)

    def test_multiple_rows(self):
        class Obj: pass

        obj1 = Obj()
        obj1.symbol = "AAPL"
        obj1.entry_price = 150.0
        obj1.exit_price = 155.5
        obj1.profit = 5.5

        obj2 = Obj()
        obj2.symbol = "GOOG"
        obj2.entry_price = 100.0
        obj2.exit_price = 110.0
        obj2.profit = 10.0

        logger = CSVLogger(filename=self.filename, fieldnames=self.fieldnames)
        logger.write(obj1)
        logger.write(obj2)

        expected = (
            "symbol,entry_price,exit_price,profit\n"
            "AAPL,150.0,155.5,5.5\n"
            "GOOG,100.0,110.0,10.0\n"
        )
        self.assertEqual(self.read_csv_as_string(), expected)

    def test_missing_fields(self):
        class Obj: pass
        obj = Obj()
        obj.symbol = "MSFT"
        obj.entry_price = 200.0
        # exit_price and profit are missing

        logger = CSVLogger(filename=self.filename, fieldnames=self.fieldnames)
        logger.write(obj)

        expected = (
            "symbol,entry_price,exit_price,profit\n"
            "MSFT,200.0,,\n"
        )
        self.assertEqual(self.read_csv_as_string(), expected)

    def test_float_precision(self):
        class Obj: pass
        obj = Obj()
        obj.symbol = "TSLA"
        obj.entry_price = 123.456789
        obj.exit_price = 234.567891
        obj.profit = 111.111102

        logger = CSVLogger(filename=self.filename, fieldnames=self.fieldnames)
        logger.write(obj)

        expected = (
            "symbol,entry_price,exit_price,profit\n"
            "TSLA,123.456789,234.567891,111.111102\n"
        )
        self.assertEqual(self.read_csv_as_string(), expected)

class TestPositionsHistoryLogger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.filename = os.path.join(self.temp_dir.name, "history.csv")

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_csv_as_string(self):
        with open(self.filename, "r", encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")

    def test_positions_history_logger_writes_expected_fields(self):
        pos = Position(
            symbol="BTCUSDT",
            interval="1h",
            candle_time=1,
            open_time="2023-01-01 00:00:00",
            entry=100,
            initial_sl=90,
            initial_tp=120,
            sl=160,
            tp=180,
            status="STOP LOSS HIT",
            type="Long",
            start_timestamp=time.time(),
            close_time="2023-01-01 01:05:30",
            duration="01:05:30",
            exit_price=90,
            exit_reason="SL",
            rr_ratio=1.5,
            profit=5
        )

        logger = PositionsHistoryLogger(filename=self.filename)
        logger.write(pos)

        expected = (
            "type,symbol,interval,entry,initial_sl,initial_tp,exit_price,open_time,close_time,duration,profit\n"
            "Long,BTCUSDT,1h,100,90,120,90,2023-01-01 00:00:00,2023-01-01 01:05:30,01:05:30,5\n"
        )
        content = self.read_csv_as_string()
        self.assertEqual(content, expected)

class TestCurrentPositionsLogger(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.filename = os.path.join(self.temp_dir.name, "current.csv")

    def tearDown(self):
        self.temp_dir.cleanup()

    def read_csv_as_string(self):
        with open(self.filename, "r", encoding="utf-8") as f:
            return f.read().replace("\r\n", "\n")

    def test_overwrites_file_on_each_write(self):
        pos1 = Position(
            symbol="BTCUSDT",
            interval="1h",
            candle_time=1,
            open_time="2023-01-01 00:00:00",
            entry=100,
            initial_sl=90,
            initial_tp=120,
            sl=160,
            tp=180,
            status="OPEN",
            type="Long",
            start_timestamp=time.time(),
            close_time="",
            duration="",
            exit_price="",
            exit_reason="",
            rr_ratio=1.5,
            profit=-1
        )
        pos1.id = 100
        pos1.current_sl=160
        pos1.next_tp=180
        pos1.current_profit=5
        pos1.current_price=102981

        pos2 = Position(
            symbol="ETHUSDT",
            interval="4h",
            candle_time=2,
            open_time="2023-01-01 04:00:00",
            entry=200,
            initial_sl=180,
            initial_tp=240,
            sl=260,
            tp=280,
            status="OPEN",
            type="Short",
            start_timestamp=time.time(),
            close_time="",
            duration="",
            exit_price="",
            exit_reason="",
            rr_ratio=2.0,
            profit=-1
        )
        pos2.id = 101
        pos2.current_sl=260
        pos2.next_tp=280
        pos2.current_profit=3
        pos2.current_price = 3362

        logger = CurrentPositionsLogger(filename=self.filename)

        # First write
        logger.write([pos1, pos2])
        print(self.read_csv_as_string())
        expected1 = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
            f"{pos1.id},{pos1.type},{pos1.symbol},{pos1.interval},{pos1.open_time},{pos1.entry},{pos1.initial_sl},{pos1.current_sl},{pos1.next_tp},{pos1.current_profit},{pos1.current_price}\n"
            f"{pos2.id},{pos2.type},{pos2.symbol},{pos2.interval},{pos2.open_time},{pos2.entry},{pos2.initial_sl},{pos2.current_sl},{pos2.next_tp},{pos2.current_profit},{pos2.current_price}\n"
        )
        self.assertEqual(self.read_csv_as_string(), expected1)

        # Second write (should overwrite)
        logger.write([pos2])
        expected2 = (
            "id,type,symbol,interval,open_time,entry,initial_sl,current_sl,next_tp,current_profit,current_price\n"
            f"{pos2.id},{pos2.type},{pos2.symbol},{pos2.interval},{pos2.open_time},{pos2.entry},{pos2.initial_sl},{pos2.current_sl},{pos2.next_tp},{pos2.current_profit},{pos2.current_price}\n"
        )
        self.assertEqual(self.read_csv_as_string(), expected2)