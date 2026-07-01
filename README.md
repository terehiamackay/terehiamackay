## Hi there 👋
👩‍💻 I'm currently working on an agent called Elisha beliving for double portion in capacity 🤺 and mad skills 🥷

---

## Slack → Jira Agent

An agent that listens to Slack conversations and creates Jira tickets from them, then posts the ticket link back to Slack.

### How it works

| Trigger | What happens |
|---|---|
| `/create-jira` slash command in a channel or thread | Collects the conversation, creates a Jira ticket, and posts the link back |
| Adding a `:jira:` reaction to any message | Collects the thread, creates a Jira ticket, and replies in-thread |

### Quick start

#### 1. Create a Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**.
2. Under **OAuth & Permissions** add these **Bot Token Scopes**:
   - `channels:history`, `groups:history`, `im:history`, `mpim:history`
   - `chat:write`
   - `commands`
   - `reactions:read`
   - `users:read`
3. Under **Slash Commands** create `/create-jira`.
4. Under **Event Subscriptions** → **Subscribe to bot events** add `reaction_added`.
5. Under **Socket Mode** enable Socket Mode and generate an **App-Level Token** with the `connections:write` scope.
6. Install the app to your workspace and copy the **Bot User OAuth Token** (`xoxb-…`).

#### 2. Configure environment variables

```bash
cp .env.example .env
# Fill in all values in .env
```

| Variable | Description |
|---|---|
| `SLACK_BOT_TOKEN` | Bot OAuth token (`xoxb-…`) |
| `SLACK_SIGNING_SECRET` | Signing secret from Basic Information |
| `SLACK_APP_TOKEN` | App-level token for Socket Mode (`xapp-…`) |
| `JIRA_SERVER` | Base URL, e.g. `https://your-org.atlassian.net` |
| `JIRA_EMAIL` | Atlassian account email |
| `JIRA_API_TOKEN` | Jira API token (create at id.atlassian.com) |
| `JIRA_PROJECT_KEY` | Key of the target project, e.g. `ENG` |
| `JIRA_ISSUE_TYPE` | Issue type (default: `Task`) |

#### 3. Install dependencies & run

```bash
pip install -r requirements.txt
python src/agent.py
```

### Project structure

```
src/
  agent.py          # Entry point – reads env vars and starts the app
  slack_handler.py  # Slack Bolt app, slash command & reaction handlers
  jira_handler.py   # Jira API client and description builder
tests/
  test_jira_handler.py
  test_slack_handler.py
requirements.txt
.env.example
```

### Running tests

```bash
pip install pytest
pytest tests/ -v
```

<!--
**terehiamackay/terehiamackay** is a ✨ _special_ ✨ repository because its `README.md` (this file) appears on your GitHub profile.
-->
