from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from ..database.database import get_db
from ..models import models
from ..schemas import schemas

router = APIRouter(prefix="/social-media", tags=["social-media"])

@router.get("/twitter-mentions", response_model=List[schemas.TwitterMention])
def get_twitter_mentions(
    sentiment: Optional[str] = None,
    category: Optional[str] = None,
    is_responded: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(models.TwitterMention)
    
    if sentiment:
        query = query.filter(models.TwitterMention.sentiment == sentiment)
    if category:
        query = query.filter(models.TwitterMention.category == category)
    if is_responded is not None:
        query = query.filter(models.TwitterMention.is_responded == is_responded)
    
    mentions = query.order_by(models.TwitterMention.timestamp.desc()).all()
    return mentions

@router.get("/twitter-mentions/{mention_id}", response_model=schemas.TwitterMention)
def get_twitter_mention(mention_id: str, db: Session = Depends(get_db)):
    mention = db.query(models.TwitterMention).filter(models.TwitterMention.id == mention_id).first()
    if not mention:
        raise HTTPException(status_code=404, detail="Twitter mention not found")
    return mention

@router.post("/twitter-mentions", response_model=schemas.TwitterMention)
def create_twitter_mention(mention: schemas.TwitterMentionCreate, db: Session = Depends(get_db)):
    # Check if tweet already exists
    existing = db.query(models.TwitterMention).filter(
        models.TwitterMention.tweet_id == mention.tweet_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Tweet already exists")
    
    mention_count = db.query(models.TwitterMention).count()
    db_mention = models.TwitterMention(
        id=f"mention-{mention_count + 1}",
        **mention.dict()
    )
    db.add(db_mention)
    db.commit()
    db.refresh(db_mention)
    return db_mention

@router.put("/twitter-mentions/{mention_id}/respond")
def respond_to_mention(
    mention_id: str,
    response_text: str,
    db: Session = Depends(get_db)
):
    mention = db.query(models.TwitterMention).filter(models.TwitterMention.id == mention_id).first()
    if not mention:
        raise HTTPException(status_code=404, detail="Twitter mention not found")
    
    mention.is_responded = True
    mention.response_text = response_text
    mention.response_at = datetime.utcnow()
    
    db.commit()
    db.refresh(mention)
    return mention

@router.get("/twitter-mentions/statistics/summary")
def get_twitter_statistics(db: Session = Depends(get_db)):
    total_mentions = db.query(models.TwitterMention).count()
    responded = db.query(models.TwitterMention).filter(
        models.TwitterMention.is_responded == True
    ).count()
    
    positive = db.query(models.TwitterMention).filter(
        models.TwitterMention.sentiment == "positive"
    ).count()
    negative = db.query(models.TwitterMention).filter(
        models.TwitterMention.sentiment == "negative"
    ).count()
    neutral = db.query(models.TwitterMention).filter(
        models.TwitterMention.sentiment == "neutral"
    ).count()
    
    complaints = db.query(models.TwitterMention).filter(
        models.TwitterMention.category == "complaint"
    ).count()
    appreciation = db.query(models.TwitterMention).filter(
        models.TwitterMention.category == "appreciation"
    ).count()
    
    return {
        "total_mentions": total_mentions,
        "responded": responded,
        "pending_response": total_mentions - responded,
        "positive_sentiment": positive,
        "negative_sentiment": negative,
        "neutral_sentiment": neutral,
        "complaints": complaints,
        "appreciation": appreciation
    }
