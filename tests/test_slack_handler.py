"""Unit tests for slack_handler helpers."""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch, call

# Ensure src/ is on the path when running tests from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ---------------------------------------------------------------------------
# Isolate Slack Bolt import so tests don't need a running Slack connection.
# ---------------------------------------------------------------------------
slack_bolt_mock = MagicMock()
slack_sdk_mock = MagicMock()
sys.modules.setdefault("slack_bolt", slack_bolt_mock)
sys.modules.setdefault("slack_bolt.adapter", MagicMock())
sys.modules.setdefault("slack_bolt.adapter.socket_mode", MagicMock())

from slack_handler import (  # noqa: E402
    _extract_summary,
    _fetch_channel_messages,
    _fetch_thread_messages,
    _resolve_user_names,
)


# ---------------------------------------------------------------------------
# _extract_summary
# ---------------------------------------------------------------------------

class TestExtractSummary:
    def test_uses_first_non_empty_message(self):
        msgs = [
            {"text": "", "user_name": "A"},
            {"text": "Real content here", "user_name": "B"},
        ]
        assert _extract_summary(msgs) == "Real content here"

    def test_strips_slack_mentions(self):
        msgs = [{"text": "<@U12345> please fix this", "user_name": "A"}]
        assert "<@" not in _extract_summary(msgs)
        assert "please fix this" in _extract_summary(msgs)

    def test_truncates_long_text(self):
        msgs = [{"text": "x" * 100, "user_name": "A"}]
        result = _extract_summary(msgs)
        assert len(result) <= 80

    def test_returns_fallback_for_empty_list(self):
        assert _extract_summary([]) == "Slack conversation"

    def test_returns_fallback_for_all_empty_text(self):
        msgs = [{"text": "", "user_name": "A"}, {"text": "   ", "user_name": "B"}]
        assert _extract_summary(msgs) == "Slack conversation"


# ---------------------------------------------------------------------------
# _resolve_user_names
# ---------------------------------------------------------------------------

class TestResolveUserNames:
    def _make_client(self, display_name="Alice"):
        client = MagicMock()
        client.users_info.return_value = {
            "user": {"profile": {"display_name": display_name, "real_name": ""}}
        }
        return client

    def test_adds_user_name_field(self):
        client = self._make_client("Alice")
        msgs = [{"user": "U001", "text": "hi"}]
        enriched = _resolve_user_names(client, msgs)
        assert enriched[0]["user_name"] == "Alice"

    def test_caches_api_calls(self):
        client = self._make_client("Bob")
        msgs = [
            {"user": "U001", "text": "first"},
            {"user": "U001", "text": "second"},
        ]
        _resolve_user_names(client, msgs)
        # users_info should only be called once for the same user.
        client.users_info.assert_called_once()

    def test_falls_back_to_uid_on_error(self):
        client = MagicMock()
        client.users_info.side_effect = Exception("API error")
        msgs = [{"user": "U999", "text": "hi"}]
        enriched = _resolve_user_names(client, msgs)
        assert enriched[0]["user_name"] == "U999"

    def test_handles_missing_user_key(self):
        client = MagicMock()
        msgs = [{"text": "no user key"}]
        enriched = _resolve_user_names(client, msgs)
        # Should not raise; user_name may be empty string.
        assert "user_name" in enriched[0]


# ---------------------------------------------------------------------------
# _fetch_thread_messages / _fetch_channel_messages
# ---------------------------------------------------------------------------

class TestFetchMessages:
    def test_fetch_thread_returns_messages(self):
        client = MagicMock()
        client.conversations_replies.return_value = {
            "messages": [{"text": "thread msg"}]
        }
        msgs = _fetch_thread_messages(client, "C001", "1234.5678")
        assert msgs == [{"text": "thread msg"}]
        client.conversations_replies.assert_called_once_with(
            channel="C001", ts="1234.5678", limit=20
        )

    def test_fetch_channel_reverses_messages(self):
        client = MagicMock()
        client.conversations_history.return_value = {
            "messages": [{"text": "b"}, {"text": "a"}]
        }
        msgs = _fetch_channel_messages(client, "C001", latest="now")
        # Should be reversed so oldest first.
        assert msgs == [{"text": "a"}, {"text": "b"}]

    def test_fetch_thread_empty_response(self):
        client = MagicMock()
        client.conversations_replies.return_value = {}
        msgs = _fetch_thread_messages(client, "C001", "ts")
        assert msgs == []
