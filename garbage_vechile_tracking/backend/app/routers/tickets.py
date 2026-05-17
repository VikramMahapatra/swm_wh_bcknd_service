from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..database.database import get_db
from ..models import models
from ..schemas import schemas
from ..routers.auth import get_current_user

router = APIRouter(prefix="/tickets", tags=["tickets"])

@router.get("/", response_model=List[schemas.Ticket])
def get_tickets(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    zone_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.Ticket)
    
    if status:
        query = query.filter(models.Ticket.status == status)
    if priority:
        query = query.filter(models.Ticket.priority == priority)
    if category:
        query = query.filter(models.Ticket.category == category)
    if zone_id:
        query = query.filter(models.Ticket.zone_id == zone_id)
    
    tickets = query.order_by(models.Ticket.created_at.desc()).all()
    return tickets

@router.get("/{ticket_id}", response_model=schemas.Ticket)
def get_ticket(ticket_id: str, db: Session = Depends(get_db)):
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return ticket

@router.post("/", response_model=schemas.Ticket)
def create_ticket(ticket: schemas.TicketCreate, db: Session = Depends(get_db)):
    # Generate ticket number
    ticket_count = db.query(models.Ticket).count()
    ticket_number = f"TKT-{ticket_count + 1:06d}"
    
    db_ticket = models.Ticket(
        id=f"ticket-{ticket_count + 1}",
        ticket_number=ticket_number,
        **ticket.dict()
    )
    db.add(db_ticket)
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

@router.put("/{ticket_id}", response_model=schemas.Ticket)
def update_ticket(
    ticket_id: str,
    ticket_update: schemas.TicketBase,
    db: Session = Depends(get_db)
):
    db_ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    for key, value in ticket_update.dict(exclude_unset=True).items():
        setattr(db_ticket, key, value)
    
    db_ticket.updated_at = datetime.utcnow()
    
    # If status is resolved or closed, set resolved_at
    if ticket_update.status in ["resolved", "closed"] and not db_ticket.resolved_at:
        db_ticket.resolved_at = datetime.utcnow()
    
    db.commit()
    db.refresh(db_ticket)
    return db_ticket

@router.get("/{ticket_id}/comments", response_model=List[schemas.TicketComment])
def get_ticket_comments(ticket_id: str, db: Session = Depends(get_db)):
    comments = db.query(models.TicketComment).filter(
        models.TicketComment.ticket_id == ticket_id
    ).order_by(models.TicketComment.created_at.asc()).all()
    return comments

@router.post("/{ticket_id}/comments", response_model=schemas.TicketComment)
def add_ticket_comment(
    ticket_id: str,
    comment: schemas.TicketCommentBase,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify ticket exists
    ticket = db.query(models.Ticket).filter(models.Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    db_comment = models.TicketComment(
        ticket_id=ticket_id,
        user_id=current_user.id,
        comment=comment.comment,
        is_internal=comment.is_internal
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment

@router.get("/statistics/summary")
def get_ticket_statistics(db: Session = Depends(get_db)):
    total_tickets = db.query(models.Ticket).count()
    open_tickets = db.query(models.Ticket).filter(models.Ticket.status == "open").count()
    in_progress = db.query(models.Ticket).filter(models.Ticket.status == "in_progress").count()
    resolved = db.query(models.Ticket).filter(models.Ticket.status == "resolved").count()
    closed = db.query(models.Ticket).filter(models.Ticket.status == "closed").count()
    
    high_priority = db.query(models.Ticket).filter(
        models.Ticket.priority.in_(["high", "critical"]),
        models.Ticket.status.in_(["open", "in_progress"])
    ).count()
    
    return {
        "total_tickets": total_tickets,
        "open_tickets": open_tickets,
        "in_progress": in_progress,
        "resolved": resolved,
        "closed": closed,
        "high_priority_open": high_priority
    }
