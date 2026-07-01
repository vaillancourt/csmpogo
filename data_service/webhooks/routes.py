"""
Golbat Webhook Routes

Receives raw Golbat webhook payloads and dispatches pokemon events to the
Discord bot manager for zone/POI filtering and Discord notification.

Golbat sends a JSON array of events:
[
  {
    "type": "pokemon",
    "message": {
      "pokemon_id": 147,
      "form": 190,
      "latitude": 45.57,
      "longitude": -73.33,
      "disappear_time": 1234567890,
      ...
    }
  },
  ...
]

Always returns HTTP 200 to suppress Golbat automatic retries on transient errors.
"""

import logging
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from data_service.discord_bot.bot import get_bot_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


@router.post("/webhook")
async def handle_webhook(request: Request) -> JSONResponse:
    """
    Receive Golbat webhook events.

    Iterates through the event array, extracts pokemon events, and forwards
    each to the Discord bot manager for zone/POI matching and notification.

    Always returns 200 — Golbat will retry on non-200 responses, which is
    undesirable for transient errors.
    """
    try:
        body = await request.json()
    except Exception as e:
        logger.warning("Failed to parse webhook body as JSON: %s", e)
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": "Invalid JSON body"},
        )

    if not isinstance(body, list):
        logger.warning("Webhook received non-list payload (type: %s)", type(body).__name__)
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": "Expected a JSON array"},
        )

    logger.debug("Webhook received: %d event(s)", len(body))

    bot_manager = get_bot_manager()
    processed = 0
    matched = 0
    skipped = 0

    for event in body:
        event_type = event.get("type", "unknown")

        if event_type != "pokemon":
            logger.debug("Skipping non-pokemon event type: %r", event_type)
            skipped += 1
            continue

        message: dict = event.get("message", {})
        processed += 1

        try:
            was_sent = bot_manager.check_and_notify(message)
            if was_sent:
                matched += 1
        except Exception as e:
            logger.error("Error processing pokemon event: %s", e, exc_info=True)

    logger.info(
        "Webhook batch done — matched: %d, processed: %d, skipped: %d",
        matched, processed, skipped,
    )

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "matched": matched,
            "processed": processed,
            "skipped": skipped,
        },
    )
