
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend import models, schemas

from backend.ai_engine import (
    generate_support_response,
    analyze_ticket
)

from backend.memory import (
    create_customer_memory_bank,
    recall_customer_memory,
    store_customer_memory
)


# Initialize database
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


# --------------------------------------------------
# HOME AND HEALTH APIs
# --------------------------------------------------

@app.get("/")
def home():
    return {
        "message": "Welcome to ResolveIQ API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# --------------------------------------------------
# CUSTOMER APIs
# --------------------------------------------------

@app.post("/customers", response_model=schemas.CustomerResponse)
def create_customer(
    customer: schemas.CustomerCreate,
    db: Session = Depends(get_db)
):
    existing = db.query(models.Customer).filter(
        models.Customer.email == customer.email
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Customer email already exists"
        )

    new_customer = models.Customer(
        name=customer.name,
        email=customer.email
    )

    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)

    # Automatically create a separate memory bank
    try:
        create_customer_memory_bank(new_customer.id)

    except Exception:
        raise HTTPException(
            status_code=502,
            detail=(
                f"Customer {new_customer.id} was created, "
                "but memory bank initialization failed. "
                "Do not submit the customer again."
            )
        )

    return new_customer


@app.get("/customers", response_model=list[schemas.CustomerResponse])
def get_customers(db: Session = Depends(get_db)):
    return db.query(models.Customer).order_by(
        models.Customer.id.desc()
    ).all()


# --------------------------------------------------
# TICKET APIs
# --------------------------------------------------

@app.post("/tickets", response_model=schemas.TicketResponse)
def create_ticket(
    ticket: schemas.TicketCreate,
    db: Session = Depends(get_db)
):
    customer = db.query(models.Customer).filter(
        models.Customer.id == ticket.customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    if ticket.priority not in [
        "low", "normal", "high", "urgent"
    ]:
        raise HTTPException(
            status_code=400,
            detail="Invalid ticket priority"
        )

    new_ticket = models.Ticket(
        customer_id=ticket.customer_id,
        subject=ticket.subject,
        description=ticket.description,
        priority=ticket.priority
    )

    db.add(new_ticket)
    db.commit()
    db.refresh(new_ticket)

    return new_ticket


@app.get("/tickets", response_model=list[schemas.TicketResponse])
def get_tickets(db: Session = Depends(get_db)):
    return db.query(models.Ticket).order_by(
        models.Ticket.id.desc()
    ).all()


@app.get("/tickets/{ticket_id}", response_model=schemas.TicketResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    ticket = db.query(models.Ticket).filter(
        models.Ticket.id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    return ticket


# --------------------------------------------------
# AI RESPONSE API
# --------------------------------------------------

@app.post("/ai/respond", response_model=schemas.AIResponse)
def ai_respond(request: schemas.AIRequest):
    try:
        answer = generate_support_response(
            issue=request.issue,
            customer_history=request.customer_history
        )

        return {"response": answer}

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI service is temporarily unavailable."
        )


# --------------------------------------------------
# AI TICKET ANALYSIS API
# --------------------------------------------------

@app.post(
    "/ai/analyze",
    response_model=schemas.TicketAnalysisResponse
)
def analyze_customer_ticket(request: schemas.AIRequest):
    try:
        result = analyze_ticket(request.issue)
        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="AI ticket analysis is temporarily unavailable."
        )


# --------------------------------------------------
# MEMORY-POWERED AI CHAT API
# --------------------------------------------------

@app.post(
    "/ai/memory-chat",
    response_model=schemas.MemoryChatResponse
)
def memory_chat(
    request: schemas.MemoryChatRequest,
    db: Session = Depends(get_db)
):
    customer = db.query(models.Customer).filter(
        models.Customer.id == request.customer_id
    ).first()

    if not customer:
        raise HTTPException(
            status_code=404,
            detail="Customer not found"
        )

    if not request.issue.strip():
        raise HTTPException(
            status_code=400,
            detail="Customer issue cannot be empty"
        )

    try:
        # Retrieve previous customer interactions
        memories = recall_customer_memory(
            request.customer_id,
            request.issue
        )

        history = "\n".join(memories)

        # Generate AI response using customer history
        answer = generate_support_response(
            issue=request.issue,
            customer_history=history
        )

        # Store current interaction
        store_customer_memory(
            request.customer_id,
            (
                f"Customer issue: {request.issue}\n"
                f"Support response: {answer}"
            )
        )

        return {
            "customer_id": request.customer_id,
            "previous_memories": memories,
            "response": answer
        }

    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Customer memory or AI service is unavailable."
        )

# --------------------------------------------------
# TICKET STATUS MANAGEMENT
# --------------------------------------------------

@app.patch("/tickets/{ticket_id}/status")
def update_ticket_status(
    ticket_id: int,
    status: str,
    db: Session = Depends(get_db)
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

    ticket = db.query(models.Ticket).filter(
        models.Ticket.id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    ticket.status = status

    db.commit()
    db.refresh(ticket)

    return {
        "message": "Ticket status updated successfully",
        "ticket_id": ticket.id,
        "status": ticket.status
    }

# --------------------------------------------------
# SAVE AI TICKET ANALYSIS
# --------------------------------------------------

@app.post("/tickets/{ticket_id}/analyze")
def analyze_and_save_ticket(
    ticket_id: int,
    db: Session = Depends(get_db)
):
    # Find ticket
    ticket = db.query(models.Ticket).filter(
        models.Ticket.id == ticket_id
    ).first()

    if not ticket:
        raise HTTPException(
            status_code=404,
            detail="Ticket not found"
        )

    try:
        # Analyze ticket using Groq AI
        result = analyze_ticket(ticket.description)

        # Validate AI response
        required_fields = [
            "category",
            "sentiment",
            "priority",
            "summary"
        ]

        if not all(
            field in result and result[field]
            for field in required_fields
        ):
            raise ValueError("AI returned incomplete analysis.")

        # Check whether analysis already exists
        analysis = db.query(models.TicketAnalysis).filter(
            models.TicketAnalysis.ticket_id == ticket_id
        ).first()

        if analysis:

            # Update existing analysis
            analysis.category = result["category"]
            analysis.sentiment = result["sentiment"]
            analysis.priority = result["priority"]
            analysis.summary = result["summary"]

        else:

            # Create new analysis
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

        return {
            "message": "Ticket analyzed and saved successfully",
            "ticket_id": ticket_id,
            "category": analysis.category,
            "sentiment": analysis.sentiment,
            "priority": analysis.priority,
            "summary": analysis.summary
        }

    except ValueError as error:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="AI analysis could not be saved."
        )

# --------------------------------------------------
# GET SAVED TICKET ANALYSES
# --------------------------------------------------

@app.get("/ticket-analyses")
def get_ticket_analyses(
    db: Session = Depends(get_db)
):
    analyses = db.query(
        models.TicketAnalysis
    ).order_by(
        models.TicketAnalysis.id.desc()
    ).all()

    return [
        {
            "id": item.id,
            "ticket_id": item.ticket_id,
            "category": item.category,
            "sentiment": item.sentiment,
            "priority": item.priority,
            "summary": item.summary,
            "analyzed_at": item.analyzed_at
        }
        for item in analyses
    ]
