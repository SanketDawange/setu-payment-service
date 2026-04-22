from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)

    transactions = relationship("Transaction", back_populates="merchant")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String, primary_key=True, index=True)
    merchant_id = Column(String, ForeignKey("merchants.id"), index=True)
    amount = Column(Float)
    currency = Column(String)
    status = Column(String, index=True)  # payment_initiated, payment_processed, payment_failed, settled
    is_settled = Column(DateTime, nullable=True) # Timestamp when it was settled
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    merchant = relationship("Merchant", back_populates="transactions")
    events = relationship("Event", back_populates="transaction")

class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, index=True) # event_id from incoming event
    transaction_id = Column(String, ForeignKey("transactions.id"), index=True)
    event_type = Column(String)
    amount = Column(Float)
    currency = Column(String)
    timestamp = Column(DateTime)
    
    transaction = relationship("Transaction", back_populates="events")

# Indexes for performance
Index("idx_transaction_merchant_status", Transaction.merchant_id, Transaction.status)
Index("idx_transaction_created_at", Transaction.created_at)
