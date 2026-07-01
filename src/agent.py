"""Entry point for the Slack-to-Jira agent."""

import logging
import os
import sys

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load environment variables from a .env file (if present).
# ---------------------------------------------------------------------------
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        logger.error("Required environment variable %s is not set.", name)
        sys.exit(1)
    return value


def main() -> None:
    """Bootstrap and run the Slack-to-Jira agent."""
    # Slack credentials
    slack_bot_token = _require_env("SLACK_BOT_TOKEN")
    slack_signing_secret = _require_env("SLACK_SIGNING_SECRET")
    slack_app_token = _require_env("SLACK_APP_TOKEN")  # required for Socket Mode

    # Jira credentials
    jira_server = _require_env("JIRA_SERVER")
    jira_email = _require_env("JIRA_EMAIL")
    jira_api_token = _require_env("JIRA_API_TOKEN")
    jira_project_key = _require_env("JIRA_PROJECT_KEY")
    jira_issue_type = os.getenv("JIRA_ISSUE_TYPE", "Task")

    # Lazy import keeps startup errors readable.
    from jira_handler import JiraHandler
    from slack_handler import create_slack_app, start_socket_mode

    jira = JiraHandler(
        server=jira_server,
        email=jira_email,
        api_token=jira_api_token,
        project_key=jira_project_key,
        issue_type=jira_issue_type,
    )

    app = create_slack_app(
        bot_token=slack_bot_token,
        signing_secret=slack_signing_secret,
        jira_handler=jira,
    )

    start_socket_mode(app, slack_app_token)


if __name__ == "__main__":
    main()
