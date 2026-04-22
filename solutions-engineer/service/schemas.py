from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class EventBase(BaseModel):
    event_id: str
    event_type: str
    transaction_id: str
    merchant_id: str
    merchant_name: str
    amount: float
    currency: str
    timestamp: datetime

class EventCreate(EventBase):
    pass

class EventResponse(BaseModel):
    id: str
    event_type: str
    timestamp: datetime

    class Config:
        from_attributes = True

class MerchantResponse(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: str
    merchant_id: str
    amount: float
    currency: str
    status: str
    created_at: datetime
    updated_at: datetime
    is_settled: Optional[datetime] = None

    class Config:
        from_attributes = True

class TransactionDetailResponse(TransactionResponse):
    merchant: MerchantResponse
    events: List[EventResponse]

class ReconciliationSummary(BaseModel):
    merchant_id: str
    merchant_name: str
    date: str
    status: str
    count: int
    total_amount: float

class DiscrepancyResponse(BaseModel):
    transaction_id: str
    merchant_id: str
    status: str
    issue: str
