"""Jira handler: creates Jira tickets from Slack conversation content."""

import logging
from dataclasses import dataclass
from typing import Optional

from jira import JIRA, JIRAError

logger = logging.getLogger(__name__)


@dataclass
class JiraTicket:
    key: str
    url: str
    summary: str


class JiraHandler:
    """Wraps the Jira REST API to create tickets from Slack conversations."""

    def __init__(
        self,
        server: str,
        email: str,
        api_token: str,
        project_key: str,
        issue_type: str = "Task",
    ) -> None:
        self.project_key = project_key
        self.issue_type = issue_type
        self.server = server.rstrip("/")
        self._client = JIRA(
            server=self.server,
            basic_auth=(email, api_token),
        )

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def create_ticket(
        self,
        summary: str,
        description: str,
        labels: Optional[list[str]] = None,
    ) -> JiraTicket:
        """Create a Jira ticket and return its key and URL.

        Args:
            summary: One-line title for the ticket.
            description: Full body (supports Jira wiki markup or plain text).
            labels: Optional list of Jira labels to apply.

        Returns:
            A JiraTicket dataclass with key, url, and summary.

        Raises:
            JIRAError: if the Jira API returns an error.
        """
        fields: dict = {
            "project": {"key": self.project_key},
            "summary": summary,
            "description": description,
            "issuetype": {"name": self.issue_type},
        }
        if labels:
            fields["labels"] = labels

        logger.info("Creating Jira ticket: %s", summary)
        issue = self._client.create_issue(fields=fields)
        url = f"{self.server}/browse/{issue.key}"
        logger.info("Created Jira ticket %s → %s", issue.key, url)
        return JiraTicket(key=issue.key, url=url, summary=summary)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def build_description(messages: list[dict]) -> str:
        """Convert a list of Slack message dicts into a Jira description.

        Each message dict is expected to contain at minimum:
            - ``user_name``: display name of the Slack user
            - ``text``: message body

        Optional key:
            - ``ts``: Slack timestamp (shown as a label if present)
        """
        lines = ["*Slack Conversation*", "----"]
        for msg in messages:
            user = msg.get("user_name", "Unknown")
            text = msg.get("text", "")
            ts = msg.get("ts", "")
            prefix = f"[{ts}] " if ts else ""
            lines.append(f"*{user}:* {prefix}{text}")
        return "\n".join(lines)
