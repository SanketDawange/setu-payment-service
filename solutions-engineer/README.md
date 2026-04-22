# Payment Lifecycle Service - Setu Hiring Assignment

A production-minded backend service to ingest payment events, manage transaction states, and provide reconciliation reports.

## Architecture Overview

- **Framework**: FastAPI (Python)
- **Database**: SQLite (SQLAlchemy ORM)
- **Validation**: Pydantic
- **Design Patterns**: 
  - **Idempotency**: Handled at the database level using unique `event_id`. Duplicate event submissions are ignored.
  - **State Machine**: Transaction status is updated based on incoming lifecycle events (`initiated` -> `processed`/`failed` -> `settled`).
  - **Reconciliation**: Aggregations and discrepancy detection are performed using optimized SQL queries.

## Setup Instructions

### Prerequisites
- Python 3.8+
- `pip`

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/SetuHQ/hiring-assignments.git
   cd solutions-engineer
   ```

2. **Navigate to the service directory**:
   ```bash
   cd service
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the service**:
   ```bash
   uvicorn main:app --reload
   ```
   The API will be available at `http://127.0.0.1:8000`. Documentation (Swagger UI) is available at `http://127.0.0.1:8000/docs`.

### Data Ingestion

To load the sample events into the database:
1. Ensure the service is running.
2. Run the ingestion script:
   ```bash
   python ingest_data.py
   ```

## API Documentation

### 1. Ingest Event
- **Endpoint**: `POST /events`
- **Description**: Accepts a payment lifecycle event.
- **Idempotency**: If the `event_id` has already been processed, the service returns the existing transaction state without duplicates.

### 2. List Transactions
- **Endpoint**: `GET /transactions`
- **Query Params**: `merchant_id`, `status`, `start_date`, `end_date`, `skip`, `limit`, `sort_by`, `sort_order`.

### 3. Fetch Transaction Details
- **Endpoint**: `GET /transactions/{transaction_id}`
- **Description**: Returns transaction details, current status, and full event history.

### 4. Reconciliation Summary
- **Endpoint**: `GET /reconciliation/summary`
- **Description**: Returns summaries grouped by merchant, date, and status.

### 5. Reconciliation Discrepancies
- **Endpoint**: `GET /reconciliation/discrepancies`
- **Description**: Identifies inconsistent states such as:
  - Settlements recorded for failed payments.
  - Settlements recorded without a processed event.

## Assumptions and Tradeoffs

1. **Database**: Used SQLite for ease of local setup. For a large-scale production system, PostgreSQL or a distributed database would be used.
2. **State Transitions**: The system follows a linear progression for statuses. In real scenarios, complex retries might require more sophisticated state handling.
3. **Performance**: Indexes were added to `merchant_id`, `status`, and `created_at` to ensure efficient filtering and aggregations on 10,000+ records.
4. **Dates**: Summary grouping uses the `created_at` timestamp (ingestion time) for grouping. In a production environment, grouping by business date (from the event payload) would be preferred.
