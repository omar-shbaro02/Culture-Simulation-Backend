import logging
import os

import httpx

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"


def _env(name: str) -> str:
    return os.getenv(name, "").strip()


def notifications_enabled() -> bool:
    return all(
        [
            _env("RESEND_API_KEY"),
            _env("RESEND_FROM_EMAIL"),
            _env("ADMIN_NOTIFICATION_EMAIL"),
        ]
    )


async def send_signup_notification(user_email: str, approved: bool) -> None:
    if not notifications_enabled():
        logger.info("Skipping signup notification email because Resend is not configured.")
        return

    frontend_app_url = _env("FRONTEND_APP_URL").rstrip("/")
    admin_review_url = f"{frontend_app_url}/admin" if frontend_app_url else ""
    approval_status = "approved automatically" if approved else "awaiting approval"

    html = f"""
    <h2>New Culture Simulation signup</h2>
    <p><strong>Email:</strong> {user_email}</p>
    <p><strong>Status:</strong> {approval_status}</p>
    <p>Open the admin panel to approve access and assign roles.</p>
    {"<p><a href='" + admin_review_url + "'>Open admin panel</a></p>" if admin_review_url else ""}
    """.strip()

    payload = {
        "from": _env("RESEND_FROM_EMAIL"),
        "to": [_env("ADMIN_NOTIFICATION_EMAIL")],
        "subject": f"New signup request: {user_email}",
        "html": html,
        "text": (
            f"New Culture Simulation signup\n\n"
            f"Email: {user_email}\n"
            f"Status: {approval_status}\n"
            f"{'Admin panel: ' + admin_review_url if admin_review_url else ''}"
        ).strip(),
    }

    headers = {
        "Authorization": f"Bearer {_env('RESEND_API_KEY')}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(RESEND_API_URL, json=payload, headers=headers)

        if response.status_code >= 400:
            logger.warning(
                "Resend signup notification failed with status %s: %s",
                response.status_code,
                response.text,
            )
    except httpx.HTTPError as exc:
        logger.warning("Resend signup notification request failed: %s", exc)
