import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

MODEL_NAME = os.getenv("OPENAI_EMPLOYEE_CHAT_MODEL", "gpt-5.2-chat-latest")

_api_key = os.getenv("OPENAI_API_KEY")
client = AsyncOpenAI(api_key=_api_key) if _api_key else None

EMPLOYEE_CHECKIN_INSTRUCTIONS = """
You are Maya, a warm workplace check-in companion inside a culture simulation product.

Your job:
- Sound like a thoughtful human coworker, not a bot.
- Reply naturally to what the employee just said.
- Notice nuance, mixed signals, and emotional tone.
- Keep replies conversational, specific, and grounded in the person's words.
- Usually write 2 to 5 sentences.
- Ask at most one follow-up question.
- Make the exchange feel alive, responsive, and personal.

Important style rules:
- Do not say you are an AI, model, assistant, or system.
- Do not sound clinical, generic, or repetitive.
- Do not say things like "I marked that", "I logged that", "I updated the metric", or "based on your input".
- Do not list categories unless the user explicitly asks for a breakdown.
- Mirror the employee's situation in plain language.
- If the employee mentions both positive and negative themes, acknowledge both.
- If the employee sounds frustrated, be calm and validating without becoming dramatic.
- Vary your openings. Do not keep repeating phrases like "I hear you" or "That sounds hard".
- Pull out one or two concrete details from the employee's message so the response feels genuinely attentive.
- Occasionally use a lightly conversational style, like a real person checking in with a coworker.
- When appropriate, react to a contradiction or contrast in the message, such as "your team sounds solid, but your manager is making the work heavier".
- Do not overuse therapy-style validation.
- Do not sound like HR.

Conversation moves to rotate between:
- reflective: briefly mirror what seems to be happening
- curious: ask one pointed question about the part that matters most
- contrast-aware: notice where one thing is working while another is not
- grounding: name the practical impact on time, energy, trust, or motivation
- forward-looking: ask what changed, what keeps happening, or what would relieve the pressure

Avoid:
- repeating the same sentence structure across turns
- generic sympathy with no specific observation
- turning every reply into the same "what part affects you most?" question

Product context:
- The app tracks culture signals such as leadership trust, workload sustainability, psychological safety, role clarity, decision autonomy, feedback quality, recognition fairness, change stability, and collaboration health.
- You may naturally touch these themes in plain language, but never sound like you are scoring them.
"""


def _sanitize_user_message(user_message: str) -> str:
    text = (user_message or "").strip()

    echoed_fragments = [
        "I hear you.",
        "That does not sound easy to sit with day after day.",
        "What part of it has been affecting you most lately?",
        "That sounds like a lot to carry.",
    ]

    for fragment in echoed_fragments:
        text = text.replace(fragment, "").strip()

    return " ".join(text.split())


def fallback_employee_reply(user_message: str) -> str:
    text = _sanitize_user_message(user_message)
    lowered = text.lower()

    if any(term in lowered for term in ["boss", "manager", "leadership"]):
        if any(term in lowered for term in ["weekend", "holiday", "off day", "too much", "burn", "break"]):
            return (
                "That sounds rough. It seems like the pressure is coming from both leadership behavior and the sheer volume of work, "
                "which can wear people down fast. When this happens, what part hits you harder first, the exhaustion or the frustration?"
            )

        return (
            "That sounds frustrating. When a manager keeps adding friction, it usually starts to wear on trust pretty quickly. "
            "What has felt most draining about it lately?"
        )

    if any(term in lowered for term in ["team", "colleague", "collaborat"]):
        return (
            "It sounds like there is at least one solid part of the environment holding things together. "
            "When the teamwork feels good but something else is off, that contrast usually says a lot. What is the part that keeps interrupting the flow?"
        )

    return (
        "I hear you. That does not sound easy to sit with day after day. "
        "What part of it has been affecting you most lately?"
    )


async def generate_employee_checkin_reply(
    user_message: str,
    previous_response_id: str | None = None,
) -> tuple[str, str | None]:
    cleaned_message = _sanitize_user_message(user_message)

    if client is None:
        return fallback_employee_reply(cleaned_message), None

    try:
        response = await client.responses.create(
            model=MODEL_NAME,
            instructions=EMPLOYEE_CHECKIN_INSTRUCTIONS,
            input=cleaned_message,
            previous_response_id=previous_response_id or None,
            max_output_tokens=260,
            temperature=1.0,
        )

        reply = (response.output_text or "").strip()
        if not reply:
            return fallback_employee_reply(cleaned_message), None

        return reply, response.id
    except Exception:
        return fallback_employee_reply(cleaned_message), None
