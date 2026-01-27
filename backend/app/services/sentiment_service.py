from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from fastapi import HTTPException, status
from datetime import datetime, timedelta
from app.models.sentiment import SentimentPoll

class SentimentService:
    def cast_vote(self, db: Session, user_id: int | None, ip_address: str, symbol: str, vote_type: str) -> SentimentPoll:
        """
        Casts a sentiment vote with rate limiting (1 vote per user/IP per asset per 24h).
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=24)

        # Build query filters
        # Check against user_id (if logged in) OR ip_address
        # AND symbol AND recently voted
        
        filters = [
            SentimentPoll.symbol == symbol,
            SentimentPoll.timestamp > cutoff_time
        ]

        if user_id is not None:
            # If user is logged in, check user_id OR ip_address
            filters.append(or_(SentimentPoll.user_id == user_id, SentimentPoll.ip_address == ip_address))
        else:
            # If guest, check ip_address only
            filters.append(SentimentPoll.ip_address == ip_address)

        existing_vote = db.query(SentimentPoll).filter(and_(*filters)).first()

        if existing_vote:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="You can only vote once per 24 hours for this asset."
            )

        # Create new vote
        new_vote = SentimentPoll(
            user_id=user_id,
            ip_address=ip_address,
            symbol=symbol,
            vote_type=vote_type
        )
        db.add(new_vote)
        db.commit()
        db.refresh(new_vote)
        
        return new_vote

sentiment_service = SentimentService()
