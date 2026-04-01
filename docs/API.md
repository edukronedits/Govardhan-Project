# API Documentation

## Base URL
```
https://api.billprocessing.example.com/v1
```

## Authentication
All API endpoints require authentication using OAuth 2.0 Bearer tokens.

```bash
curl -H "Authorization: Bearer <token>" \
  https://api.billprocessing.example.com/v1/documents
```

---

## Endpoints

### Health Check

**GET** `/health`

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "service": "bill-processing-api"
}
```

---

### Document Management

#### Upload Document

**POST** `/documents`

Upload a new bill for processing.

**Request Body:**
```json
{
  "vendor_name": "ABC Corporation",
  "bill_date": "2024-01-15",
  "bill_amount": 2500.00,
  "source": "api"
}
```

**Response (202 Accepted):**
```json
{
  "ingestion_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "ingested",
  "message": "Document queued for processing",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### Get Document

**GET** `/documents/{ingestion_id}`

Retrieve processing results for a document.

**Response (200 OK):**
```json
{
  "ingestion_id": "550e8400-e29b-41d4-a716-446655440000",
  "extraction_result": {
    "vendor_name": "ABC Corporation",
    "invoice_id": "INV-2024-001",
    "invoice_date": "2024-01-15",
    "total_amount": 2500.00,
    "overall_confidence": 0.94,
    "requires_manual_review": false
  },
  "validation_result": {
    "overall_status": "passed",
    "passed_rules": 18,
    "failed_rules": 0,
    "review_required_rules": 1
  },
  "status": "completed",
  "processing_timestamp": "2024-01-15T10:35:00Z"
}
```

#### List Documents

**GET** `/documents?skip=0&limit=50&vendor_name=ABC&status=completed`

List documents with filtering.

**Query Parameters:**
- `skip`: Pagination offset (default: 0)
- `limit`: Pagination limit (default: 50)
- `vendor_name`: Filter by vendor
- `status`: Filter by status (completed|failed|pending)

**Response (200 OK):**
```json
[
  {
    "ingestion_id": "550e8400-e29b-41d4-a716-446655440000",
    "extraction_result": {...},
    "validation_result": {...},
    "status": "completed"
  }
]
```

#### Submit Review

**PUT** `/documents/{ingestion_id}/review`

Submit manual review for a document.

**Request Body:**
```json
{
  "reviewer_id": "user@example.com",
  "corrections": {
    "vendor_name": "ABC Corporation Inc.",
    "total_amount": 2600.00
  },
  "notes": "Corrected vendor name and total"
}
```

**Response (200 OK):**
```json
{
  "ingestion_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "reviewed",
  "review_timestamp": "2024-01-15T10:40:00Z"
}
```

---

### Business Rules

#### Create Rule

**POST** `/rules`

Create a new business rule.

**Request Body:**
```json
{
  "rule_id": "RULE-VENDOR-APPROVAL",
  "name": "Vendor Approval Check",
  "rule_type": "deterministic",
  "condition": "data.get('vendor_approved', False)",
  "action": "Check vendor is in approved list",
  "priority": 10,
  "enabled": true
}
```

**Response (201 Created):**
```json
{
  "rule_id": "RULE-VENDOR-APPROVAL",
  "name": "Vendor Approval Check",
  "rule_type": "deterministic",
  "condition": "data.get('vendor_approved', False)",
  "action": "Check vendor is in approved list",
  "priority": 10,
  "enabled": true
}
```

#### List Rules

**GET** `/rules?enabled_only=false`

List all business rules.

**Query Parameters:**
- `enabled_only`: Return only enabled rules (default: false)

**Response (200 OK):**
```json
[
  {
    "rule_id": "RULE-VENDOR-APPROVAL",
    "name": "Vendor Approval Check",
    ...
  }
]
```

#### Get Rule

**GET** `/rules/{rule_id}`

Get a specific rule.

**Response (200 OK):**
```json
{
  "rule_id": "RULE-VENDOR-APPROVAL",
  "name": "Vendor Approval Check",
  ...
}
```

#### Update Rule

**PUT** `/rules/{rule_id}`

Update an existing rule.

**Request Body:** Same as Create Rule

**Response (200 OK):** Updated rule

#### Delete Rule

**DELETE** `/rules/{rule_id}`

Delete a rule.

**Response (204 No Content)**

---

### Batch Operations

#### Batch Ingest

**POST** `/batch/ingest`

Ingest multiple documents in batch.

**Request Body:**
```json
{
  "batch_id": "BATCH-001",
  "documents": [
    {
      "vendor_name": "Vendor A",
      "bill_date": "2024-01-15",
      "bill_amount": 1000.00
    },
    {
      "vendor_name": "Vendor B",
      "bill_date": "2024-01-15",
      "bill_amount": 2000.00
    }
  ],
  "priority": 5
}
```

**Response (202 Accepted):**
```json
{
  "batch_id": "BATCH-001",
  "ingestion_ids": [
    "550e8400-e29b-41d4-a716-446655440000",
    "550e8400-e29b-41d4-a716-446655440001"
  ],
  "total_documents": 2,
  "status": "queued",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### Analytics

#### Get Summary

**GET** `/analytics/summary`

Get processing analytics and metrics.

**Response (200 OK):**
```json
{
  "total_documents_processed": 1250,
  "passed_validations": 1180,
  "failed_validations": 50,
  "requires_review": 20,
  "accuracy_rate": 0.944,
  "total_rules": 45,
  "enabled_rules": 40,
  "queued_documents": 15,
  "timestamp": "2024-01-15T10:40:00Z"
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Validation failed",
  "details": ["Missing required field: vendor_name"]
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "detail": "Missing or invalid authentication token"
}
```

### 404 Not Found
```json
{
  "error": "Document not found",
  "detail": "No document with ID: 550e8400-e29b-41d4-a716-446655440000"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal server error",
  "detail": "An unexpected error occurred"
}
```

---

## Rate Limiting

API requests are rate limited to prevent abuse.

**Limits:**
- 1000 requests per minute per API key
- 10000 requests per hour per API key

**Response Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1705315800
```

---

## Pagination

List endpoints support cursor-based pagination.

**Parameters:**
- `skip`: Number of items to skip
- `limit`: Maximum items to return (max: 100)

**Example:**
```
GET /documents?skip=0&limit=50
```

---

## Webhooks

Subscribe to processing events via webhooks.

**Supported Events:**
- `document.ingested`
- `document.processing_complete`
- `document.validation_failed`
- `rule.created`
- `rule.updated`

**Creating a Webhook:**
```bash
curl -X POST https://api.billprocessing.example.com/webhooks \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["document.processing_complete"],
    "active": true
  }'
```

---

## SDKs

Official SDKs available for:
- Python: `pip install bill-processing-sdk`
- JavaScript/Node.js: `npm install @billprocessing/sdk`
- .NET: `dotnet add package BillProcessing.SDK`

---

## Support

For API issues and questions:
- Email: api-support@billprocessing.example.com
- Documentation: https://docs.billprocessing.example.com
- Issues: https://github.com/billprocessing/api-issues
