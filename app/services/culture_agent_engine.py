from openai import OpenAI
from app.services.knowledge_registry import get_dimension_knowledge

client = OpenAI()

BASE_SYSTEM_PROMPT = '''
You are a Culture Intelligence Advisor.
You specialize in organizational culture analysis.
Stay grounded in behavioral science frameworks.
Give actionable leadership advice.
Avoid generic motivation or vague coaching.
'''

def ask_culture_agent(dimension_slug: str, user_message: str):

    knowledge = get_dimension_knowledge(dimension_slug)

    if not knowledge:
        return "No knowledge found for this dimension."

    system_prompt = f"""
{BASE_SYSTEM_PROMPT}

Dimension: {knowledge.get("name")}

Drivers:
{knowledge.get("drivers")}

Frameworks:
{knowledge.get("frameworks")}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.4,
    )

    return response.choices[0].message.content
