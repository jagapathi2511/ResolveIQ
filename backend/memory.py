
import os

from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

_client = None


def get_hindsight_client():
    global _client

    if _client is None:
        api_key = os.getenv("HINDSIGHT_API_KEY")
        base_url = os.getenv(
            "HINDSIGHT_BASE_URL",
            "https://api.hindsight.vectorize.io"
        )

        if not api_key:
            raise ValueError("HINDSIGHT_API_KEY is missing from .env")

        _client = Hindsight(
            base_url=base_url,
            api_key=api_key
        )

    return _client


def create_customer_memory_bank(customer_id: int):
    client = get_hindsight_client()

    bank_id = f"customer-{customer_id}"

    bank = client.create_bank(
        bank_id=bank_id,
        name=f"ResolveIQ Customer {customer_id}",
        background=(
            "Customer support history, reported issues, "
            "troubleshooting attempts, failed solutions, "
            "and verified resolutions."
        )
    )

    return bank.bank_id


def store_customer_memory(customer_id: int, content: str):
    client = get_hindsight_client()

    bank_id = f"customer-{customer_id}"

    client.retain(
        bank_id=bank_id,
        content=content,
        context="ResolveIQ customer support interaction"
    )

    return "Customer memory stored successfully"


def recall_customer_memory(customer_id: int, query: str):
    client = get_hindsight_client()

    bank_id = f"customer-{customer_id}"

    result = client.recall(
        bank_id=bank_id,
        query=query
    )

    return [memory.text for memory in result.results]

def store_troubleshooting_memory(
    customer_id: int,
    ticket_id: int,
    step: str,
    outcome: str,
    notes: str = ""
):
    client = get_hindsight_client()

    bank_id = f"customer-{customer_id}"

    content = f"""
Customer ID: {customer_id}
Ticket ID: {ticket_id}
Troubleshooting step: {step}
Outcome: {outcome}
Additional notes: {notes if notes else "No additional notes."}

Remember the exact outcome:
- suggested means only recommended
- attempted means customer tried it
- failed means it did not solve the issue
- successful means customer confirmed it worked
"""

    client.retain(
        bank_id=bank_id,
        content=content,
        context="ResolveIQ troubleshooting history"
    )

    return "Troubleshooting memory stored successfully"
