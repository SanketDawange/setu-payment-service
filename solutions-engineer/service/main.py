from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import models, schemas, crud
from database import engine, get_db

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Payment Lifecycle Service")

@app.post("/events", response_model=schemas.TransactionResponse)
def ingest_event(event: schemas.EventCreate, db: Session = Depends(get_db)):
    return crud.create_event(db=db, event=event)

@app.get("/transactions", response_model=List[schemas.TransactionResponse])
def list_transactions(
    merchant_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: Session = Depends(get_db)
):
    return crud.get_transactions(
        db, merchant_id=merchant_id, status=status, 
        start_date=start_date, end_date=end_date, 
        skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order
    )

@app.get("/transactions/{transaction_id}", response_model=schemas.TransactionDetailResponse)
def get_transaction_details(transaction_id: str, db: Session = Depends(get_db)):
    db_transaction = crud.get_transaction(db, transaction_id=transaction_id)
    if db_transaction is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return db_transaction

@app.get("/reconciliation/summary", response_model=List[schemas.ReconciliationSummary])
def get_reconciliation_summary(db: Session = Depends(get_db)):
    return crud.get_reconciliation_summary(db)

@app.get("/reconciliation/discrepancies", response_model=List[schemas.DiscrepancyResponse])
def get_reconciliation_discrepancies(db: Session = Depends(get_db)):
    return crud.get_discrepancies(db)

@app.get("/")
def read_root():
    return {"message": "Setu Hiring Assignment - Payment Lifecycle Service"}
