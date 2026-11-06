from contextlib import asynccontextmanager

from fastapi import (
    FastAPI,
    Depends,
    HTTPException
)
from fastapi.security import (
    HTTPBearer,
    HTTPAuthorizationCredentials
)
from jose import JWTError
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend import models, schemas
from backend.database import engine, get_db, Base

from backend.ai_engine import (
    generate_support_response,
    analyze_ticket,
    generate_memory_insights
)

from backend.memory import (
    create_customer_memory_bank,
    store_customer_memory,
    recall_customer_memory,
    store_troubleshooting_memory
)

from backend.auth import (
    hash_password,
    verify_password,
    create_access_token,
    verify_access_token
)


# ==================================================
# JWT AUTHENTICATION
# ==================================================

security = HTTPBearer()


def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    token = credentials.credentials

    try:
        payload = verify_access_token(token)
        customer_id = int(payload.get("sub"))

    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    customer = db.query(models.Customer).filter(
        models.Customer.id == customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=401,
            detail="Customer not found"
        )

    return customer


# ==================================================
# CHECK TICKET OWNERSHIP
# ==================================================

def get_owned_ticket(
    ticket_id: int,
    current_customer: models.Customer,
    db: Session
):
    ticket = db.query(models.Ticket).filter(
        models.Ticket.id == ticket_id,
        models.Ticket.customer_id == current_customer.id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    return ticket


# ==================================================
# DATABASE STARTUP
# ==================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="ResolveIQ API",
    description="AI-Powered Customer Support Memory Agent",
    version="1.0.0",
    lifespan=lifespan
)


# ==================================================
# HOME AND HEALTH
# ==================================================

@app.get("/")
def home():
    return {
        "message": "Welcome to ResolveIQ API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ==================================================
# CUSTOMER REGISTRATION
# ==================================================

@app.post(
    "/customers",
    response_model=schemas.CustomerResponse
)
def create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(get_db)
):

    existing_customer = db.query(
        models.Customer
    ).filter(
        models.Customer.email == customer.email
    ).first()

    if existing_customer:
        raise HTTPException(
            status_code=400,
            detail="Customer email already exists"
        )

    new_customer = models.Customer(
        name=customer.name,
        email=customer.email,
        password_hash=hash_password(customer.password)
    )

    db.add(new_customer)

    try:
        db.commit()
        db.refresh(new_customer)

    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Customer email already exists"
        )

    try:
        create_customer_memory_bank(new_customer.id)

    except Exception as e:
        print("Memory bank creation error:", str(e))

    return new_customer


# ==================================================
# CUSTOMER LOGIN
# ==================================================

@app.post(
    "/login",
    response_model=schemas.TokenResponse
)
def login_customer(
    credentials: schemas.CustomerLogin,
    db: Session = Depends(get_db)
):

    customer = db.query(models.Customer).filter(
        models.Customer.email == credentials.email
    ).first()

    if not customer or not customer.password_hash:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if not verify_password(
        credentials.password,
        customer.password_hash
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    access_token = create_access_token({
        "sub": str(customer.id)
    })

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


# ==================================================
# GET LOGGED-IN CUSTOMER
# ==================================================

@app.get(
    "/customers",
    response_model=list[schemas.CustomerResponse]
)
def get_customers(
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(
        get_current_customer
    )
):

    return db.query(models.Customer).filter(
        models.Customer.id == current_customer.id
    ).all()


# ==================================================
# CREATE TICKET
# ==================================================

@app.post(
    "/tickets",
    response_model=schemas.TicketResponse
)
def create_ticket(
    ticket: schemas.TicketCreate,
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    new_ticket = models.Ticket(
        customer_id=current_customer.id,
        subject=ticket.subject,
        description=ticket.description,
        status="open",
        priority="normal"
    )

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    return new_ticket


# ==================================================
# GET LOGGED-IN CUSTOMER TICKETS
# ==================================================

@app.get(
    "/tickets",
    response_model=list[schemas.TicketResponse]
)
def get_tickets(
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(
        get_current_customer
    )
):

    return db.query(models.Ticket).filter(
        models.Ticket.customer_id == current_customer.id
    ).all()


# ==================================================
# GET INDIVIDUAL TICKET
# ==================================================

@app.get(
    "/tickets/{ticket_id}",
    response_model=schemas.TicketResponse
)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    ticket = get_owned_ticket(
        ticket_id,
        current_customer,
        db
    )

    return ticket


# ==================================================
# BASIC AI SUPPORT RESPONSE
# ==================================================

@app.post(
    "/ai/respond",
    response_model=schemas.AIResponse
)
def ai_respond(
    request: schemas.AIRequest,
    current_customer: models.Customer = Depends(get_current_customer)
):

    response = generate_support_response(
        request.issue,
        request.customer_history
    )

    return {"response": response}


# ==================================================
# AI TICKET ANALYSIS
# ==================================================

@app.post("/ai/analyze")
def ai_analyze(
    request: schemas.AIRequest,
    current_customer: models.Customer = Depends(get_current_customer)
):

    result = analyze_ticket(request.issue)

    return result


# ==================================================
# CUSTOMER MEMORY CHAT
# ==================================================

@app.post(
    "/ai/memory-chat",
    response_model=schemas.MemoryChatResponse
)
def memory_chat(
    request: schemas.MemoryChatRequest,
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    if request.customer_id != current_customer.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another customer's memory"
        )

    customer = current_customer

    try:
        previous_memories = recall_customer_memory(
            request.customer_id,
            request.issue
        )

    except Exception as e:
        print("Memory recall error:", str(e))
        previous_memories = []

    customer_tickets = db.query(models.Ticket).filter(
        models.Ticket.customer_id == current_customer.id
    ).all()

    troubleshooting_history = []

    for ticket in customer_tickets:

        attempts = db.query(
            models.TroubleshootingAttempt
        ).filter(
            models.TroubleshootingAttempt.ticket_id == ticket.id
        ).order_by(
            models.TroubleshootingAttempt.created_at.asc()
        ).all()

        for attempt in attempts:

            troubleshooting_history.append(
                f"""
Ticket ID: {ticket.id}
Ticket Subject: {ticket.subject}
Troubleshooting Step: {attempt.step}
Outcome: {attempt.outcome}
Notes: {attempt.notes or "No additional notes"}
"""
            )

    customer_history = ""

    if previous_memories:
        customer_history += "\nPREVIOUS CUSTOMER MEMORIES:\n"

        for memory in previous_memories:
            customer_history += f"- {memory}\n"

    if troubleshooting_history:
        customer_history += (
            "\nSTRUCTURED TROUBLESHOOTING HISTORY:\n"
        )

        for attempt in troubleshooting_history:
            customer_history += attempt + "\n"

    if not customer_history:
        customer_history = (
            "No previous customer support history found."
        )

    response = generate_support_response(
        request.issue,
        customer_history
    )

    try:
        store_customer_memory(
            current_customer.id,
            f"""
Customer ID: {current_customer.id}

Current Issue:
{request.issue}

AI Support Response:
{response}
"""
        )

    except Exception as e:
        print("Memory storage error:", str(e))

    return {
        "customer_id": current_customer.id,
        "previous_memories": previous_memories,
        "response": response
    }


# ==================================================
# UPDATE TICKET STATUS
# ==================================================

@app.patch("/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    allowed_statuses = [
        "open",
        "in_progress",
        "resolved"
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticket status"
        )

    ticket = get_owned_ticket(
        ticket_id,
        current_customer,
        db
    )

    ticket.status = status

    db.commit()
    db.refresh(ticket)

    return {
        "message": "Ticket status updated successfully",
        "ticket_id": ticket.id,
        "status": ticket.status
    }


# ==================================================
# SAVE AI TICKET ANALYSIS
# ==================================================

@app.post("/tickets/{ticket_id}/analyze")
def analyze_existing_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    ticket = get_owned_ticket(
        ticket_id,
        current_customer,
        db
    )

    result = analyze_ticket(ticket.description)

    analysis = db.query(
        models.TicketAnalysis
    ).filter(
        models.TicketAnalysis.ticket_id == ticket_id
    ).first()

    if analysis:

        analysis.category = result["category"]
        analysis.sentiment = result["sentiment"]
        analysis.priority = result["priority"]
        analysis.summary = result["summary"]

    else:

        analysis = models.TicketAnalysis(
            ticket_id=ticket_id,
            category=result["category"],
            sentiment=result["sentiment"],
            priority=result["priority"],
            summary=result["summary"]
        )

        db.add(analysis)

    db.commit()
    db.refresh(analysis)

    return analysis


# ==================================================
# GET LOGGED-IN CUSTOMER TICKET ANALYSES
# ==================================================

@app.get(
    "/ticket-analyses",
    response_model=list[schemas.TicketAnalysisResponse]
)
def get_ticket_analyses(
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    return db.query(models.TicketAnalysis).join(
        models.Ticket,
        models.TicketAnalysis.ticket_id == models.Ticket.id
    ).filter(
        models.Ticket.customer_id == current_customer.id
    ).all()


# ==================================================
# ADD TROUBLESHOOTING ATTEMPT
# ==================================================

@app.post(
    "/tickets/{ticket_id}/troubleshooting-attempts"
)
def add_troubleshooting_attempt(
    ticket_id: int,
    attempt: schemas.TroubleshootingAttemptCreate,
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    ticket = get_owned_ticket(
        ticket_id,
        current_customer,
        db
    )

    new_attempt = models.TroubleshootingAttempt(
        ticket_id=ticket_id,
        step=attempt.step,
        outcome=attempt.outcome,
        notes=attempt.notes
    )

    db.add(new_attempt)
    db.commit()
    db.refresh(new_attempt)

    try:
        store_troubleshooting_memory(
            customer_id=current_customer.id,
            ticket_id=ticket_id,
            step=attempt.step,
            outcome=attempt.outcome,
            notes=attempt.notes or ""
        )

        hindsight_status = "stored successfully"

    except Exception as e:
        print("Troubleshooting memory error:", str(e))
        hindsight_status = "storage failed"

    return {
        "message": "Troubleshooting attempt saved",
        "attempt_id": new_attempt.id,
        "ticket_id": ticket_id,
        "step": new_attempt.step,
        "outcome": new_attempt.outcome,
        "notes": new_attempt.notes,
        "hindsight_memory": hindsight_status
    }


# ==================================================
# GET TROUBLESHOOTING ATTEMPTS
# ==================================================

@app.get(
    "/tickets/{ticket_id}/troubleshooting-attempts"
)
def get_troubleshooting_attempts(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    ticket = get_owned_ticket(
        ticket_id,
        current_customer,
        db
    )

    attempts = db.query(
        models.TroubleshootingAttempt
    ).filter(
        models.TroubleshootingAttempt.ticket_id == ticket_id
    ).order_by(
        models.TroubleshootingAttempt.created_at.asc()
    ).all()

    return attempts


# ==================================================
# CUSTOMER TROUBLESHOOTING FEEDBACK
# ==================================================

@app.post(
    "/tickets/{ticket_id}/troubleshooting-feedback"
)
def submit_troubleshooting_feedback(
    ticket_id: int,
    feedback: schemas.TroubleshootingFeedback,
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    ticket = get_owned_ticket(
        ticket_id,
        current_customer,
        db
    )

    if feedback.customer_id != current_customer.id:
        raise HTTPException(
            status_code=403,
            detail="Customer ID does not match the logged-in account"
        )

    outcome = (
        "successful"
        if feedback.successful
        else "failed"
    )

    notes = feedback.notes or ""

    attempt = models.TroubleshootingAttempt(
        ticket_id=ticket_id,
        step="Customer feedback on suggested solution",
        outcome=outcome,
        notes=notes
    )

    db.add(attempt)

    if feedback.successful:
        ticket.status = "resolved"
    else:
        ticket.status = "in_progress"

    db.commit()
    db.refresh(attempt)
    db.refresh(ticket)

    try:
        store_troubleshooting_memory(
            customer_id=current_customer.id,
            ticket_id=ticket_id,
            step="Customer feedback on suggested solution",
            outcome=outcome,
            notes=notes
        )

        memory_status = "stored successfully"

    except Exception as e:
        print("Hindsight feedback storage error:", str(e))
        memory_status = "storage failed"

    return {
        "message": "Customer feedback recorded",
        "ticket_id": ticket_id,
        "outcome": outcome,
        "ticket_status": ticket.status,
        "hindsight_memory": memory_status
    }


# ==================================================
# AUTOMATIC NEXT-STEP RECOMMENDATION
# ==================================================

@app.post(
    "/tickets/{ticket_id}/next-recommendation"
)
def generate_next_recommendation(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    ticket = get_owned_ticket(
        ticket_id,
        current_customer,
        db
    )

    attempts = db.query(
        models.TroubleshootingAttempt
    ).filter(
        models.TroubleshootingAttempt.ticket_id == ticket_id
    ).order_by(
        models.TroubleshootingAttempt.created_at.asc()
    ).all()

    history = []

    for attempt in attempts:
        history.append(
            f"Step: {attempt.step}\n"
            f"Outcome: {attempt.outcome}\n"
            f"Notes: {attempt.notes or 'None'}"
        )

    customer_history = "\n\n".join(history)

    try:
        memories = recall_customer_memory(
            current_customer.id,
            ticket.description
        )

        if memories:
            customer_history += (
                "\n\nPREVIOUS CUSTOMER MEMORIES:\n"
                + "\n".join(memories)
            )

    except Exception as e:
        print("Memory recall error:", str(e))

    issue = f"""
Original ticket subject: {ticket.subject}

Customer problem:
{ticket.description}

IMPORTANT:
Review all previous troubleshooting attempts.
Do not repeat failed solutions.
Suggest the next appropriate troubleshooting step.
If more information is needed, ask the customer a question.
"""

    response = generate_support_response(
        issue,
        customer_history
    )

    try:
        store_customer_memory(
            current_customer.id,
            f"""
Ticket ID: {ticket_id}

New troubleshooting recommendation:
{response}

Status: Suggested, not yet attempted.
"""
        )

        memory_status = "stored successfully"

    except Exception as e:
        print("Memory storage error:", str(e))
        memory_status = "storage failed"

    return {
        "ticket_id": ticket_id,
        "customer_id": current_customer.id,
        "previous_attempts": len(attempts),
        "recommendation": response,
        "memory_status": memory_status
    }


# ==================================================
# AI CUSTOMER MEMORY INSIGHTS
# ==================================================

@app.get("/customers/{customer_id}/memory-insights")
def get_customer_memory_insights(
    customer_id: int,
    db: Session = Depends(get_db),
    current_customer: models.Customer = Depends(get_current_customer)
):

    if customer_id != current_customer.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another customer's memory insights"
        )

    customer = current_customer

    tickets = db.query(models.Ticket).filter(
        models.Ticket.customer_id == current_customer.id
    ).all()

    history = []

    history.append(f"Customer Name: {customer.name}")
    history.append(f"Customer ID: {current_customer.id}")

    for ticket in tickets:

        history.append(f"\nTicket ID: {ticket.id}")
        history.append(f"Subject: {ticket.subject}")
        history.append(f"Issue: {ticket.description}")
        history.append(f"Status: {ticket.status}")
        history.append(f"Priority: {ticket.priority}")

        attempts = db.query(
            models.TroubleshootingAttempt
        ).filter(
            models.TroubleshootingAttempt.ticket_id == ticket.id
        ).all()

        for attempt in attempts:

            history.append(
                f"Troubleshooting Step: {attempt.step}"
            )

            history.append(
                f"Outcome: {attempt.outcome}"
            )

            history.append(
                f"Notes: {attempt.notes or 'No notes'}"
            )

    customer_history = "\n".join(history)

    if not tickets:
        customer_history += (
            "\nNo previous support tickets are available."
        )

    try:
        insights = generate_memory_insights(
            customer_history
        )

        return {
            "customer_id": current_customer.id,
            "customer_name": customer.name,
            "total_tickets": len(tickets),
            "insights": insights
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"AI memory insights failed: {str(error)}"
        )