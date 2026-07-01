"""Unit tests for JiraHandler."""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Ensure src/ is on the path when running tests from the repo root.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from jira_handler import JiraHandler, JiraTicket  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_jira_client():
    """Return a MagicMock that mimics jira.JIRA."""
    with patch("jira_handler.JIRA") as mock_cls:
        instance = MagicMock()
        mock_cls.return_value = instance
        yield instance


@pytest.fixture()
def handler(mock_jira_client):
    return JiraHandler(
        server="https://example.atlassian.net",
        email="user@example.com",
        api_token="token123",
        project_key="ENG",
        issue_type="Task",
    )


# ---------------------------------------------------------------------------
# create_ticket
# ---------------------------------------------------------------------------

class TestCreateTicket:
    def test_returns_jira_ticket(self, handler, mock_jira_client):
        mock_issue = MagicMock()
        mock_issue.key = "ENG-42"
        mock_jira_client.create_issue.return_value = mock_issue

        ticket = handler.create_ticket(summary="Fix bug", description="Details here")

        assert isinstance(ticket, JiraTicket)
        assert ticket.key == "ENG-42"
        assert ticket.url == "https://example.atlassian.net/browse/ENG-42"
        assert ticket.summary == "Fix bug"

    def test_passes_labels_to_jira(self, handler, mock_jira_client):
        mock_issue = MagicMock()
        mock_issue.key = "ENG-1"
        mock_jira_client.create_issue.return_value = mock_issue

        handler.create_ticket(
            summary="Label test",
            description="body",
            labels=["slack", "auto"],
        )

        call_fields = mock_jira_client.create_issue.call_args[1]["fields"]
        assert call_fields["labels"] == ["slack", "auto"]

    def test_no_labels_field_when_none(self, handler, mock_jira_client):
        mock_issue = MagicMock()
        mock_issue.key = "ENG-2"
        mock_jira_client.create_issue.return_value = mock_issue

        handler.create_ticket(summary="No labels", description="body")

        call_fields = mock_jira_client.create_issue.call_args[1]["fields"]
        assert "labels" not in call_fields

    def test_project_and_issue_type_passed(self, handler, mock_jira_client):
        mock_issue = MagicMock()
        mock_issue.key = "ENG-3"
        mock_jira_client.create_issue.return_value = mock_issue

        handler.create_ticket(summary="Check fields", description="body")

        call_fields = mock_jira_client.create_issue.call_args[1]["fields"]
        assert call_fields["project"] == {"key": "ENG"}
        assert call_fields["issuetype"] == {"name": "Task"}


# ---------------------------------------------------------------------------
# build_description
# ---------------------------------------------------------------------------

class TestBuildDescription:
    def test_includes_user_and_text(self):
        msgs = [{"user_name": "Alice", "text": "Hello world", "ts": ""}]
        result = JiraHandler.build_description(msgs)
        assert "*Alice:*" in result
        assert "Hello world" in result

    def test_includes_timestamp_when_present(self):
        msgs = [{"user_name": "Bob", "text": "Hi", "ts": "1700000000.000100"}]
        result = JiraHandler.build_description(msgs)
        assert "1700000000.000100" in result

    def test_multiple_messages(self):
        msgs = [
            {"user_name": "Alice", "text": "First", "ts": ""},
            {"user_name": "Bob", "text": "Second", "ts": ""},
        ]
        result = JiraHandler.build_description(msgs)
        assert "First" in result
        assert "Second" in result

    def test_missing_user_name_falls_back_to_unknown(self):
        msgs = [{"text": "No user here"}]
        result = JiraHandler.build_description(msgs)
        assert "Unknown" in result

    def test_header_present(self):
        result = JiraHandler.build_description([])
        assert "*Slack Conversation*" in result
