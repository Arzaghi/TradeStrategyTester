import unittest
from unittest.mock import patch, MagicMock
from telegram_notifier import TelegramNotifier  # Adjust import path if needed

class TestTelegramNotifier(unittest.TestCase):
    def setUp(self):
        self.bot_token = "dummy_token"
        self.chat_id = "123456789"
        self.notifier = TelegramNotifier(self.bot_token, self.chat_id)

    @patch("telegram_notifier.requests.post")
    def test_send_message_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True, "result": {"message_id": 1}}
        mock_post.return_value = mock_response

        result = self.notifier.send_message("Hello, Telegram!")
        mock_post.assert_called_once()

        # Check URL and payload
        args, kwargs = mock_post.call_args
        self.assertIn(self.bot_token, args[0])
        self.assertEqual(kwargs["data"]["chat_id"], self.chat_id)
        self.assertEqual(kwargs["data"]["text"], "Hello, Telegram!")
        self.assertEqual(result["result"]["message_id"], 1)

    @patch("telegram_notifier.requests.post")
    def test_send_message_failure_does_not_throw(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = Exception("Forbidden")
        mock_post.return_value = mock_response

        result = self.notifier.send_message("This should fail")

        self.assertIsNone(result)
        mock_post.assert_called_once()

    @patch("telegram_notifier.requests.post")
    def test_send_message_with_html_parse_mode(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"ok": True}
        mock_post.return_value = mock_response

        self.notifier.send_message("<b>Bold text</b>", parse_mode="HTML")
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["data"]["parse_mode"], "HTML")
