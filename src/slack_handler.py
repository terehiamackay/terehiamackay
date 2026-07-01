"""Slack handler: listens for events and slash commands, creates Jira tickets."""

import logging
import re
from typing import Optional

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from jira_handler import JiraHandler, JiraTicket

logger = logging.getLogger(__name__)

# Slack message limit per history fetch (max 1000 per Slack docs).
_MAX_MESSAGES = 20


def _extract_summary(messages: list[dict]) -> str:
    """Return a short (≤ 80 char) summary derived from the first message."""
    first_text = ""
    for msg in messages:
        text = (msg.get("text") or "").strip()
        if text:
            first_text = text
            break
    # Strip Slack mention syntax (<@U…>) and trim to 80 chars.
    clean = re.sub(r"<@[A-Z0-9]+>", "", first_text).strip()
    return clean[:77] + "…" if len(clean) > 80 else clean or "Slack conversation"


def _resolve_user_names(client, messages: list[dict]) -> list[dict]:
    """Enrich each message dict with a ``user_name`` field."""
    cache: dict[str, str] = {}
    enriched = []
    for msg in messages:
        uid = msg.get("user") or msg.get("bot_id", "")
        if uid and uid not in cache:
            try:
                resp = client.users_info(user=uid)
                profile = resp["user"].get("profile", {})
                cache[uid] = (
                    profile.get("display_name")
                    or profile.get("real_name")
                    or uid
                )
            except Exception:
                cache[uid] = uid
        enriched.append({**msg, "user_name": cache.get(uid, uid)})
    return enriched


def _fetch_thread_messages(client, channel: str, thread_ts: str) -> list[dict]:
    """Fetch all replies in a thread."""
    resp = client.conversations_replies(
        channel=channel,
        ts=thread_ts,
        limit=_MAX_MESSAGES,
    )
    return resp.get("messages", [])


def _fetch_channel_messages(
    client, channel: str, latest: str, count: int = _MAX_MESSAGES
) -> list[dict]:
    """Fetch recent messages from a channel around a given timestamp."""
    resp = client.conversations_history(
        channel=channel,
        latest=latest,
        limit=count,
        inclusive=True,
    )
    messages = resp.get("messages", [])
    return list(reversed(messages))


def create_slack_app(
    bot_token: str,
    signing_secret: str,
    jira_handler: JiraHandler,
) -> App:
    """Build and return a configured Slack Bolt App.

    Registers:
    - ``/create-jira`` slash command
    - ``:jira:`` reaction-added event

    Args:
        bot_token: Slack bot OAuth token (``xoxb-…``).
        signing_secret: Slack app signing secret.
        jira_handler: Configured :class:`JiraHandler` instance.

    Returns:
        A :class:`slack_bolt.App` ready to be served.
    """
    app = App(token=bot_token, signing_secret=signing_secret)

    # ------------------------------------------------------------------
    # /create-jira  slash command
    # ------------------------------------------------------------------
    @app.command("/create-jira")
    def handle_create_jira(ack, body, client, respond):  # noqa: WPS430
        ack()
        channel_id: str = body["channel_id"]
        message_ts: Optional[str] = body.get("message_ts") or body.get("ts")
        thread_ts: Optional[str] = body.get("thread_ts")

        # Collect messages: prefer thread, fall back to recent channel history.
        if thread_ts:
            raw_messages = _fetch_thread_messages(client, channel_id, thread_ts)
        elif message_ts:
            raw_messages = _fetch_thread_messages(client, channel_id, message_ts)
        else:
            raw_messages = _fetch_channel_messages(client, channel_id, latest="now")

        if not raw_messages:
            respond("⚠️ No messages found to create a Jira ticket from.")
            return

        messages = _resolve_user_names(client, raw_messages)
        summary = _extract_summary(messages)
        description = JiraHandler.build_description(messages)

        try:
            ticket: JiraTicket = jira_handler.create_ticket(
                summary=summary,
                description=description,
                labels=["slack"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to create Jira ticket")
            respond(f"❌ Failed to create Jira ticket: {exc}")
            return

        # Post the Jira link back to the channel (or thread).
        post_kwargs: dict = {
            "channel": channel_id,
            "text": (
                f"✅ Jira ticket created: *<{ticket.url}|{ticket.key}>*\n"
                f"> {ticket.summary}"
            ),
        }
        if thread_ts:
            post_kwargs["thread_ts"] = thread_ts

        client.chat_postMessage(**post_kwargs)
        respond(f"✅ Ticket <{ticket.url}|{ticket.key}> created and posted to the channel.")

    # ------------------------------------------------------------------
    # :jira: reaction  — react to any message to turn it into a ticket
    # ------------------------------------------------------------------
    @app.event("reaction_added")
    def handle_reaction_added(event, client, say):  # noqa: WPS430
        if event.get("reaction") != "jira":
            return

        channel_id: str = event["item"]["channel"]
        message_ts: str = event["item"]["ts"]

        raw_messages = _fetch_thread_messages(client, channel_id, message_ts)
        if not raw_messages:
            # Fall back to just the reacted-to message.
            raw_messages = _fetch_channel_messages(
                client, channel_id, latest=message_ts, count=1
            )

        if not raw_messages:
            logger.warning("No messages found for reaction_added event")
            return

        messages = _resolve_user_names(client, raw_messages)
        summary = _extract_summary(messages)
        description = JiraHandler.build_description(messages)

        try:
            ticket: JiraTicket = jira_handler.create_ticket(
                summary=summary,
                description=description,
                labels=["slack"],
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to create Jira ticket via reaction")
            say(
                channel=channel_id,
                text=f"❌ Failed to create Jira ticket: {exc}",
                thread_ts=message_ts,
            )
            return

        say(
            channel=channel_id,
            text=(
                f"✅ Jira ticket created: *<{ticket.url}|{ticket.key}>*\n"
                f"> {ticket.summary}"
            ),
            thread_ts=message_ts,
        )

    return app


def start_socket_mode(app: App, app_token: str) -> None:  # pragma: no cover
    """Start the app in Socket Mode (no public URL required)."""
    handler = SocketModeHandler(app, app_token)
    logger.info("Starting Slack app in Socket Mode…")
    handler.start()
