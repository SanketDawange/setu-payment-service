from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
import models, schemas
import datetime

def get_transaction(db: Session, transaction_id: str):
    return db.query(models.Transaction).filter(models.Transaction.id == transaction_id).first()

def get_transactions(db: Session, merchant_id: str = None, status: str = None, start_date: datetime.datetime = None, end_date: datetime.datetime = None, skip: int = 0, limit: int = 100, sort_by: str = "created_at", sort_order: str = "desc"):
    query = db.query(models.Transaction)
    
    if merchant_id:
        query = query.filter(models.Transaction.merchant_id == merchant_id)
    if status:
        query = query.filter(models.Transaction.status == status)
    if start_date:
        query = query.filter(models.Transaction.created_at >= start_date)
    if end_date:
        query = query.filter(models.Transaction.created_at <= end_date)
    
    # Sorting
    attr = getattr(models.Transaction, sort_by, models.Transaction.created_at)
    if sort_order == "desc":
        query = query.order_by(attr.desc())
    else:
        query = query.order_by(attr.asc())
        
    return query.offset(skip).limit(limit).all()

def create_event(db: Session, event: schemas.EventCreate):
    # Idempotency check
    existing_event = db.query(models.Event).filter(models.Event.id == event.event_id).first()
    if existing_event:
        # If the event ID exists, it must be for the same transaction ID
        if existing_event.transaction_id != event.transaction_id:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="Event ID already exists for a different transaction")
        
        # Return the transaction associated with the existing event
        return db.query(models.Transaction).filter(models.Transaction.id == existing_event.transaction_id).first()

    # Get or create merchant
    merchant = db.query(models.Merchant).filter(models.Merchant.id == event.merchant_id).first()
    if not merchant:
        merchant = models.Merchant(id=event.merchant_id, name=event.merchant_name)
        db.add(merchant)
        db.flush()

    # Get or create transaction
    transaction = db.query(models.Transaction).filter(models.Transaction.id == event.transaction_id).first()
    if not transaction:
        transaction = models.Transaction(
            id=event.transaction_id,
            merchant_id=event.merchant_id,
            amount=event.amount,
            currency=event.currency,
            status=event.event_type,
            created_at=event.timestamp
        )
        db.add(transaction)
    else:
        # Update transaction status
        # Simple priority: initiated < processed/failed < settled
        # Note: In a real system, we'd handle timestamp-based updates more carefully
        current_status = transaction.status
        new_status = event.event_type
        
        # State transition logic
        if new_status == "settled":
            transaction.status = "settled"
            transaction.is_settled = event.timestamp
        elif new_status == "payment_processed" and current_status == "payment_initiated":
            transaction.status = "payment_processed"
        elif new_status == "payment_failed" and current_status == "payment_initiated":
            transaction.status = "payment_failed"
        # If it's already settled or failed, we generally don't move back to initiated/processed
        # but we still record the event.

    # Record event
    db_event = models.Event(
        id=event.event_id,
        transaction_id=event.transaction_id,
        event_type=event.event_type,
        amount=event.amount,
        currency=event.currency,
        timestamp=event.timestamp
    )
    db.add(db_event)
    db.commit()
    db.refresh(transaction)
    return transaction

def get_reconciliation_summary(db: Session):
    # Grouped by merchant, date, status
    # In SQLite, we use strftime for date
    summary = db.query(
        models.Transaction.merchant_id,
        models.Merchant.name.label("merchant_name"),
        func.strftime("%Y-%m-%d", models.Transaction.created_at).label("date"),
        models.Transaction.status,
        func.count(models.Transaction.id).label("count"),
        func.sum(models.Transaction.amount).label("total_amount")
    ).join(models.Merchant, models.Transaction.merchant_id == models.Merchant.id)\
     .group_by(models.Transaction.merchant_id, "date", models.Transaction.status)\
     .all()
    
    return [
        schemas.ReconciliationSummary(
            merchant_id=s[0],
            merchant_name=s[1],
            date=s[2],
            status=s[3],
            count=s[4],
            total_amount=s[5]
        ) for s in summary
    ]

def get_discrepancies(db: Session):
    discrepancies = []

    # Use select() on subqueries to avoid SQLAlchemy warnings
    subq_failed = db.query(models.Event.transaction_id).filter(models.Event.event_type == "payment_failed").subquery()
    subq_settled = db.query(models.Event.transaction_id).filter(models.Event.event_type == "settled").subquery()
    subq_processed = db.query(models.Event.transaction_id).filter(models.Event.event_type == "payment_processed").subquery()
    
    # 1. Settlement recorded for a failed payment
    failed_and_settled = db.query(models.Transaction).filter(
        models.Transaction.id.in_(db.query(subq_failed)),
        models.Transaction.id.in_(db.query(subq_settled))
    ).all()
    
    for tx in failed_and_settled:
        discrepancies.append(schemas.DiscrepancyResponse(
            transaction_id=tx.id,
            merchant_id=tx.merchant_id,
            status=tx.status,
            issue="Settlement recorded for a failed payment"
        ))

    # 2. Settled without being marked as processed
    settled_no_processed = db.query(models.Transaction).filter(
        models.Transaction.id.in_(db.query(subq_settled)),
        ~models.Transaction.id.in_(db.query(subq_processed)),
        ~models.Transaction.id.in_(db.query(subq_failed))
    ).all()

    for tx in settled_no_processed:
        discrepancies.append(schemas.DiscrepancyResponse(
            transaction_id=tx.id,
            merchant_id=tx.merchant_id,
            status=tx.status,
            issue="Settled without being marked as processed"
        ))

    # 3. Conflicting amounts (Multiple initiated events with different amounts/currencies)
    conflicting_txs = db.query(
        models.Event.transaction_id
    ).filter(models.Event.event_type == "payment_initiated")\
     .group_by(models.Event.transaction_id)\
     .having(func.count(func.distinct(models.Event.amount)) > 1).all()

    for row in conflicting_txs:
        tx_id = row[0]
        tx = get_transaction(db, tx_id)
        discrepancies.append(schemas.DiscrepancyResponse(
            transaction_id=tx_id,
            merchant_id=tx.merchant_id if tx else "unknown",
            status=tx.status if tx else "unknown",
            issue="Duplicate initiation events with conflicting amounts"
        ))

    # 4. Payment marked processed but never settled
    # We look for transactions in 'payment_processed' state that are not in the 'settled' subquery
    processed_no_settle = db.query(models.Transaction).filter(
        models.Transaction.status == "payment_processed",
        ~models.Transaction.id.in_(db.query(subq_settled))
    ).limit(50).all() # Limit to avoid overwhelming the response

    for tx in processed_no_settle:
        discrepancies.append(schemas.DiscrepancyResponse(
            transaction_id=tx.id,
            merchant_id=tx.merchant_id,
            status=tx.status,
            issue="Payment marked processed but never settled"
        ))

    return discrepancies
