import unittest
from unittest.mock import patch
from api import BinanceAPI

class TestBinanceAPI(unittest.TestCase):
    @patch("api.requests.get")
    def test_get_candles(self, mock_get):
        mock_get.return_value.json.return_value = [["dummy"]]
        mock_get.return_value.raise_for_status = lambda: None
        api = BinanceAPI()
        candles = api.get_candles("BTCUSDT", "1h")
        self.assertEqual(candles, [["dummy"]])

    @patch("api.requests.get")
    def test_get_current_price(self, mock_get):
        mock_get.return_value.json.return_value = {"price": "123.45"}
        mock_get.return_value.raise_for_status = lambda: None
        api = BinanceAPI()
        price = api.get_current_price("BTCUSDT")
        self.assertEqual(price, 123.45)
