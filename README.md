# Payment Lifecycle Service - Setu Hiring Assignment

A production-minded backend service to ingest payment events, manage transaction states, and provide reconciliation reports.

**Live Demo**: [https://setu-payment-service.onrender.com/docs](https://setu-payment-service.onrender.com/docs)
*(Note: Hosted on Render free tier; may take ~60s to load if inactive.)*

## Architecture Overview

- **Framework**: FastAPI (Python)
- **Database**: SQLite (SQLAlchemy ORM)
- **Validation**: Pydantic
- **Design Patterns**: 
  - **Idempotency**: Handled at the database level using unique `event_id` and explicit existence checks in the CRUD layer.
  - **State Machine**: Transaction status is updated based on incoming lifecycle events (`initiated` -> `processed`/`failed` -> `settled`).
  - **Reconciliation**: Aggregations and discrepancy detection are performed using optimized SQL queries to ensure performance with 10,000+ records.

## Design Decisions

### 1. SQL Schema & Indexing
- **Normalization**: Separated `Merchants`, `Transactions`, and `Events`. This ensures data integrity and allows for efficient querying of transaction history without duplicating merchant metadata.
- **Indexing Strategy**: 
    - Unique index on `Event.id` ensures absolute idempotency.
    - Foreign key indexes on `Transaction.merchant_id` and `Event.transaction_id` for fast joins.
    - Composite index on `Transaction(merchant_id, status)` to optimize the most common filtering use case.
    - Index on `Transaction.created_at` for high-performance date-range reporting.

### 2. Idempotency & Concurrency
- **Strategy**: Each event has a unique `event_id`. Before processing, we check for existence. If found, we return the current state of the associated transaction without re-processing.
- **Reliability**: This approach prevents duplicate billing or state corruption even if the client retries a request due to network timeouts.

### 3. Business Logic Location
- **SQL vs Python**: All aggregations (SUM, COUNT, GROUP BY) and complex filters (Date ranges, status filtering) are implemented at the SQL level via SQLAlchemy. This avoids "Python loops" for data processing, ensuring the service remains responsive as the dataset grows.

## Setup Instructions

### Prerequisites
- Python 3.8+
- `pip`

### Local Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/SanketDawange/setu-payment-service.git
   cd setu-payment-service/solutions-engineer/service
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Start the service**:
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
  - Duplicate initiation events with conflicting amounts.

## Deployment

- **Platform**: The service is deployed on **Render**.
- **Live URL**: [https://setu-payment-service.onrender.com/docs](https://setu-payment-service.onrender.com/docs)
- **Containerization**: A `Dockerfile` is included in the `service/` directory for consistent deployments.
- **Infrastructure**: The app runs as a web service with an ephemeral SQLite database. 
- **Cold Start**: Note that the Render free tier spins down after inactivity. The first request may take ~60 seconds to respond.

## Assumptions and Tradeoffs

1. **Database**: Used SQLite for ease of local setup. For a large-scale production system, PostgreSQL or a distributed database would be used.
2. **State Transitions**: The system follows a linear progression for statuses. In real scenarios, complex retries might require more sophisticated state handling.
3. **Performance**: Indexes were added to `merchant_id`, `status`, and `created_at` to ensure efficient filtering and aggregations on 10,000+ records.
4. **Dates**: Transactions are grouped by the business timestamp (`event.timestamp`) rather than ingestion time. This ensures reconciliation reports accurately reflect when payments actually occurred.

## Assignment Disclosure

- **Time Limit**: This assignment was completed within the 3-day window from the time it was shared.
- **Resources Used**: Standard Python documentation, FastAPI community resources, and internet research for SQL grouping best practices in SQLite.
- **AI Tool Disclosure**: This solution was developed with the assistance of **Antigravity (Google Gemini)**. The AI was used to:
  - Generate the initial boilerplate for FastAPI models and schemas.
  - Optimize SQL queries for the reconciliation reports.
  - Assist in implementing the idempotency logic and state transition rules.
  - Conduct final verification of API endpoints using automated scripts.
