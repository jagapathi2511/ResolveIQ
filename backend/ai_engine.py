
import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

MODEL_NAME = "openai/gpt-oss-120b"


def generate_support_response(issue: str, customer_history: str = "") -> str:
    """
    Generate an AI-powered customer support response.
    """

    if not GROQ_API_KEY:
        raise ValueError(
            "GROQ_API_KEY not found. Check your .env file."
        )

    if not issue.strip():
        raise ValueError("Customer issue cannot be empty.")

    client = Groq(api_key=GROQ_API_KEY)

    messages = [
        {
            "role": "system",
            "content": (
                "You are ResolveIQ, an intelligent customer support agent. "
                "Understand customer problems and provide clear, polite, "
                "practical troubleshooting steps. "
                "Consider previous customer history when available. "
                "Do not repeat troubleshooting steps that have already failed. "
                "Never claim that an issue is resolved unless verified. "
                "Never promise refunds or make account changes."
            )
        },
        {
            "role": "user",
            "content": f"""
Customer issue:
{issue}

Previous customer history:
{customer_history if customer_history else "No previous history available."}

Provide:
1. Understanding of the issue.
2. Recommended troubleshooting steps.
3. What to do if the issue continues.
"""
        }
    ]

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.4,
        max_completion_tokens=500
    )

    return response.choices[0].message.content

import json


def analyze_ticket(issue: str) -> dict:
    if not issue.strip():
        raise ValueError("Customer issue cannot be empty.")

    client = Groq(api_key=GROQ_API_KEY)

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": """
You are ResolveIQ, a customer support ticket analyzer.

Analyze the customer issue and return valid JSON only.

Use these categories:
Technical Support, Billing, Account Access,
Order/Delivery, General Inquiry, Other.

Sentiment must be Positive, Neutral, or Negative.

Priority must be low, normal, high, or urgent.

Return this JSON structure:
{
    "category": "Technical Support",
    "sentiment": "Negative",
    "priority": "high",
    "summary": "Short summary of the issue"
}
"""
            },
            {
                "role": "user",
                "content": issue
            }
        ],
        temperature=0.2,
        max_completion_tokens=300,
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)
