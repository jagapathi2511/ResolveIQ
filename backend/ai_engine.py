
import os
import json

from dotenv import load_dotenv
from groq import Groq


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL_NAME = "openai/gpt-oss-120b"

client = None


def get_groq_client():
    global client

    if client is None:
        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is missing from .env"
            )

        client = Groq(api_key=GROQ_API_KEY)

    return client


# --------------------------------------------------
# AI SUPPORT RESPONSE
# --------------------------------------------------

def generate_support_response(
    issue: str,
    customer_history: str = ""
):

    customer_history = customer_history or (
        "No previous customer support history available."
    )

    system_prompt = """
You are ResolveIQ, an intelligent AI customer support agent.

Your job is to provide accurate, practical and personalized
technical support.

IMPORTANT RULES:

1. Understand the customer's current problem before suggesting
   a solution.

2. Carefully examine the customer's previous support history.

3. NEVER recommend a troubleshooting step marked as FAILED
   again for the same issue unless there is a clear reason
   to retry it.

4. Do not confuse suggested steps with attempted steps.

5. A successful step means the customer confirmed it worked.

6. If a previous solution failed, recommend a different
   troubleshooting approach.

7. Give instructions one step at a time when practical.

8. Use simple language that customers can understand.

9. If information is insufficient, ask a relevant question.

10. Never claim that an issue is resolved without customer
    confirmation.

11. Never promise refunds, account changes or actions that
    you cannot perform.

12. Do not invent customer history or previous actions.

RESPONSE FORMAT:

Problem Understanding:
Briefly explain what you understood.

Previous History:
Mention relevant previous attempts, if available.

Recommended Solution:
Give the next appropriate troubleshooting step.

Next Action:
Ask the customer to try the step and report the result.

Keep the response clear, professional and concise.
"""

    user_prompt = f"""
CUSTOMER'S CURRENT ISSUE:

{issue}


CUSTOMER'S PREVIOUS SUPPORT HISTORY:

{customer_history}


Provide a personalized support response using the rules above.
"""

    groq_client = get_groq_client()

    completion = groq_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.3,
        max_tokens=1200
    )

    return completion.choices[0].message.content


# --------------------------------------------------
# AI TICKET ANALYSIS
# --------------------------------------------------

def analyze_ticket(issue: str):

    prompt = f"""
Analyze this customer support ticket.

Ticket:
{issue}

Return ONLY valid JSON using this exact structure:

{{
    "category": "Technical/Billing/Account/General",
    "sentiment": "Positive/Neutral/Negative",
    "priority": "low/normal/high/urgent",
    "summary": "Short summary of the issue"
}}

Classification rules:

- urgent: Critical service outage or major business impact.
- high: Serious issue affecting important functionality.
- normal: Standard support request.
- low: Minor question or inconvenience.

Do not include Markdown or explanations outside JSON.
"""

    groq_client = get_groq_client()

    completion = groq_client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2,
        max_tokens=500
    )

    response_text = completion.choices[0].message.content.strip()

    # Remove Markdown code fences if returned
    if response_text.startswith("```"):
        response_text = response_text.replace(
            "```json", ""
        ).replace("```", "").strip()

    try:
        result = json.loads(response_text)

    except json.JSONDecodeError:
        raise ValueError(
            "AI returned invalid JSON: " + response_text
        )

    required_fields = [
        "category",
        "sentiment",
        "priority",
        "summary"
    ]

    for field in required_fields:
        if field not in result:
            raise ValueError(
                f"AI analysis is missing field: {field}"
            )

    return result
# ==================================================
# AI CUSTOMER MEMORY INSIGHTS
# ==================================================

def generate_memory_insights(customer_history: str):

    client = get_groq_client()

    system_prompt = """
    You are ResolveIQ, an intelligent customer support memory analyst.

    Analyze the customer's complete support history.

    Generate a clear report with these sections:

    1. Most Common Customer Problems
    2. Previously Failed Troubleshooting Methods
    3. Most Effective Solutions
    4. Customer Issue Patterns
    5. Personalized Future Recommendations

    Important rules:
    - Use only the information provided.
    - Do not invent customer problems or solutions.
    - Distinguish successful and failed attempts.
    - If information is missing, clearly mention it.
    - Give practical recommendations.
    - Use simple professional language.
    """

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": customer_history
            }
        ],
        temperature=0.3,
        max_tokens=1500
    )

    return response.choices[0].message.content