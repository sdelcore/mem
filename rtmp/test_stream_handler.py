#!/usr/bin/env python3
"""Tests for RTMP stream handler."""

import json
import sys
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Import the module to test
sys.path.insert(0, ".")
import stream_handler


class TestStreamHandler(unittest.TestCase):
    """Test cases for stream handler functions."""

    @patch("stream_handler.httpx.Client")
    def test_notify_backend_success(self, mock_client_class):
        """Test successful backend notification."""
        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = stream_handler.notify_backend(
            "stream_start", "test-key-123", {"resolution": "1920x1080"}
        )

        self.assertTrue(result)
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        self.assertIn("/api/streams/events", call_args[0][0])

        json_data = call_args[1]["json"]
        self.assertEqual(json_data["event_type"], "stream_start")
        self.assertEqual(json_data["stream_key"], "test-key-123")
        self.assertEqual(json_data["metadata"]["resolution"], "1920x1080")

    @patch("stream_handler.httpx.Client")
    def test_notify_backend_failure(self, mock_client_class):
        """Test backend notification failure."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = stream_handler.notify_backend("stream_end", "test-key-456")

        self.assertFalse(result)

    @patch("stream_handler.httpx.Client")
    def test_notify_backend_exception(self, mock_client_class):
        """Test backend notification with exception."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)
        mock_client.post.side_effect = Exception("Connection error")
        mock_client_class.return_value = mock_client

        result = stream_handler.notify_backend("stream_error", "test-key-789")

        self.assertFalse(result)

    @patch("stream_handler.notify_backend")
    @patch("stream_handler.sys.argv", ["stream_handler.py", "start", "stream-key-123"])
    def test_main_minimal_args(self, mock_notify):
        """Test main function with minimal arguments."""
        mock_notify.return_value = True

        with self.assertRaises(SystemExit) as cm:
            stream_handler.main()

        self.assertEqual(cm.exception.code, 0)
        mock_notify.assert_called_once_with("start", "stream-key-123", {})

    @patch("stream_handler.notify_backend")
    @patch(
        "stream_handler.sys.argv",
        ["stream_handler.py", "stop", "stream-key-456", '{"duration": 3600}'],
    )
    def test_main_with_metadata(self, mock_notify):
        """Test main function with metadata."""
        mock_notify.return_value = True

        with self.assertRaises(SystemExit) as cm:
            stream_handler.main()

        self.assertEqual(cm.exception.code, 0)
        mock_notify.assert_called_once_with(
            "stop", "stream-key-456", {"duration": 3600}
        )

    @patch("stream_handler.sys.argv", ["stream_handler.py"])
    def test_main_insufficient_args(self):
        """Test main function with insufficient arguments."""
        with self.assertRaises(SystemExit) as cm:
            stream_handler.main()

        self.assertEqual(cm.exception.code, 1)

    @patch("stream_handler.notify_backend")
    @patch(
        "stream_handler.sys.argv",
        ["stream_handler.py", "error", "stream-key-789", "invalid-json"],
    )
    def test_main_invalid_json(self, mock_notify):
        """Test main function with invalid JSON metadata."""
        mock_notify.return_value = True

        with self.assertRaises(SystemExit) as cm:
            stream_handler.main()

        self.assertEqual(cm.exception.code, 0)
        # Should still call notify_backend with empty metadata
        mock_notify.assert_called_once_with("error", "stream-key-789", {})

    @patch("stream_handler.notify_backend")
    @patch("stream_handler.sys.argv", ["stream_handler.py", "publish", "test-stream"])
    def test_main_notify_failure(self, mock_notify):
        """Test main function when notification fails."""
        mock_notify.return_value = False

        with self.assertRaises(SystemExit) as cm:
            stream_handler.main()

        self.assertEqual(cm.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
