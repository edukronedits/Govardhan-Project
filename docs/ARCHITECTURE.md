# Architecture Design Document

## System Architecture Overview

The Bill Processing System employs an **event-driven microservices architecture** with serverless and containerized components on Azure.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT APPLICATIONS                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                  AZURE API MANAGEMENT (APIM)                     │
│  • Request throttling & validation                              │
│  • OAuth/JWT authentication                                     │
│  • API versioning & analytics                                   │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│              INGESTION LAYER (Azure Functions)                   │
│  • Multi-source ingestion (API, batch, streams)                 │
│  • Metadata extraction & validation                             │
│  • Request enrichment                                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────────┬──────────────────────┐
│   Azure Service Bus  │   Azure Event Hub    │
│   (queues, topics)   │   (streaming)        │
│   • Dead-letter DLQ  │   • Scale-out        │
│   • Retry policies   │   • Real-time        │
└──────────────────────┴──────────────────────┘
        ↓                       ↓
┌─────────────────────────────────────────────────────────────────┐
│           DOCUMENT PROCESSING PIPELINE                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   OCR    │→ │Clean/    │→ │ Entity   │→ │ Line-Item│       │
│  │Extract   │  │Normalize │  │Extract   │  │Extract   │       │
│  └────┬─────┘  └──────────┘  └────┬─────┘  └────┬─────┘       │
│       │ (Azure Doc Intelligence)   │ (LLM-based) │          │
│       └────────────────────────────┘────────────┘           │
│                    (Azure Databricks)                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│             AI AGENT FRAMEWORK (Azure OpenAI)                   │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │ Extractor Agent: Extract structured data from text      │  │
│  │ Business Rule Agent: Validate against business rules    │  │
│  │ Rule Prediction Agent: Predict rules for new patterns   │  │
│  └─────────────────────────────────────────────────────────┘  │
│  • Tool usage: API calls, database queries                     │
│  • Knowledge integration: Azure AI Search (vectors)            │
│  • Guardrails: Validation, confidence scores                  │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         BUSINESS RULE ENGINE (Azure Functions / AKS)           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │Deterministic │  │Probabilistic │  │AI-Inferred   │         │
│  │Rules         │  │Rules         │  │Rules         │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│  • Validation at document & line-item levels                   │
│  • Conflict resolution                                         │
│  • Rule effectiveness tracking                                 │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│         RULE GENERATION & LEARNING LOOP                         │
│  • Compare extracted vs expected                               │
│  • Detect mismatches → Flag for AI analysis                    │
│  • Generate new rules → Human validation                       │
│  • Store approved rules in knowledge base                      │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────┬────────────────────┬─────────────────────┐
│   Azure SQL      │   Azure Cosmos DB  │ Azure AI Search     │
│   (Metadata)     │   (Rules Cache)    │ (Vector Embeddings) │
│   (Audit Log)    │                    │ (Semantic Search)   │
└──────────────────┴────────────────────┴─────────────────────┘
        ↓                       ↓                       ↓
┌─────────────────────────────────────────────────────────────────┐
│              STORAGE LAYER                                      │
│  • Azure Data Lake Gen2: Raw & processed documents              │
│  • Azure Blob Storage: Document archives                        │
│  • Backup & disaster recovery replicas                         │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌──────────────────┬──────────────────────┬──────────────────┐
│  Backend API     │  Machine Learning    │   Dashboard      │
│  (App Service/   │  Pipeline (AzureML)  │   (React SPA)    │
│   AKS)           │                      │   (Static Apps)  │
└──────────────────┴──────────────────────┴──────────────────┘
        ↓
┌─────────────────────────────────────────────────────────────────┐
│         MONITORING & OBSERVABILITY                              │
│  • Azure Monitor • Application Insights • Log Analytics         │
│  • Custom dashboards • Automated alerts                         │
└─────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### 1. API Management (`APIM`)
- **Purpose**: Single entry point, API governance
- **Responsibilities**:
  - Authentication (OAuth 2.0, JWT)
  - Rate limiting & quotas
  - Request/response transformation
  - API versioning
  - Analytics & monitoring

### 2. Ingestion Service (Azure Functions)
- **Triggers**: HTTP, Service Bus, Timer
- **Functions**:
  - `IngestionHTTP`: HTTP endpoint for bill uploads
  - `BatchIngestion`: Batch processing from blob storage
  - `StreamIngestion`: Real-time stream processing

### 3. Document Processor (Databricks)
- **Pipeline**:
  1. OCR using Azure Document Intelligence
  2. Text preprocessing (normalization, cleaning)
  3. Entity extraction (vendor, dates, amounts)
  4. Line-item extraction (table parsing)
  5. Confidence scoring
  6. Data merging & deduplication

### 4. AI Agent Framework
- **Agents**:
  - `ExtractorAgent`: Extracts structured fields
  - `RuleValidatorAgent`: Validates against business rules
  - `RulePredictorAgent`: Generates new rules from mismatches

- **Capabilities**:
  - Tool calling: API endpoints, database queries
  - Memory: Short-term (conversation), Long-term (vector DB)
  - Guardrails: Validation, confidence thresholds
  - Error handling: Retry logic, fallbacks

### 5. Business Rule Engine
- **Rule Types**:
  - **Deterministic**: If-then logic, exact matches
  - **Probabilistic**: Fuzzy matching, thresholds
  - **AI-Inferred**: Generated by AI agents

- **Validation Levels**:
  - Document-level: Totals, headers, structure
  - Line-item level: Individual line validations
  - Cross-field: Relationships between fields

### 6. Orchestration Layer (Durable Functions)
- **Orchestrator Workflows**:
  - BillParserOrchestrator: End-to-end document processing
  - RuleEngineOrchestrator: Rule execution & conflict resolution

### 7. Storage Layer
| Service | Purpose | Use Case |
|---------|---------|----------|
| Azure SQL | Relational metadata | Rules, configurations, audit logs |
| Azure Cosmos DB | Document store | Extracted data, rule cache, state |
| Azure AI Search | Vector search | Embeddings, semantic queries |
| Data Lake Gen2 | Data warehouse | Raw/processed documents, analytics |
| Blob Storage | Object storage | Document archives, backups |

### 8. Backend API
- **Endpoints**:
  - `POST /documents` - Upload bill
  - `GET /documents/{id}` - Retrieve extraction
  - `GET /rules` - List active rules
  - `POST /rules` - Create rule
  - `PUT /documents/{id}/review` - Manual review

### 9. Frontend Dashboard
- **Features**:
  - Document upload & processing
  - Rule management interface
  - Mismatch visualization
  - Analytics & reporting
  - Manual review queue

## Data Flow

### Happy Path: Bill Processing Flow

```
1. INGESTION
   Client → APIM → IngestionFunction
   ↓ (validate, enrich)
   
2. QUEUE
   → Service Bus Topic
   ↓ (fan-out to processors)
   
3. DOCUMENT PROCESSING
   → Document Intelligence (OCR)
   → Databricks Pipeline (NLP)
   → Entity Extraction
   ↓ (output: extracted data)
   
4. AI EXTRACTION
   → ExtractorAgent (OpenAI)
   ↓ (refine, validate)
   
5. RULE VALIDATION
   → RuleValidatorAgent
   ↓ (check business rules)
   
6. RULE ENGINE
   → Execute rules (deterministic, probabilistic, AI)
   ↓ (output: pass/fail/review)
   
7. STORAGE
   → SQL (metadata)
   → Cosmos (extracted data)
   → Search Index (embeddings)
   ↓
   
8. RESPONSE
   ← API returns extraction results
   ← Dashboard shows for review
```

### Exception Path: Low Confidence/Mismatch

```
Extracted Data → Confidence Check
   ↓ (if low confidence or mismatch)
   → Flag for AI Analysis
   → RulePredictorAgent generates potential rules
   → Human review queue
   ↓ (if approved)
   → Store in knowledge base
   → Update rule set
   → Retrain models (async)
```

## Scalability Considerations

### Horizontal Scaling
- **Azure Functions**: Auto-scale based on queue depth
- **Service Bus**: Partitioned topics for parallelism
- **AKS**: Pod autoscaling based on CPU/memory
- **Event Hub**: Partitioned streams for throughput

### Load Distribution
- APIM: Distribute across regions
- Ingestion Functions: Scale by queue depth
- Processors: Databricks cluster auto-scaling
- Rule Engine: AKS node pool scaling

### Performance Optimization
- Caching: Azure Cache for Redis
- CDN: Azure CDN for static assets
- Database optimization: Indexing, partitioning
- Async processing: For non-critical operations

## Security Architecture

### Authentication & Authorization
- **APIM**: OAuth 2.0 / OpenID Connect
- **AAD Integration**: Azure Entra ID for internal services
- **Service-to-Service**: Managed identities

### Data Protection
- **Encryption in Transit**: TLS 1.2+
- **Encryption at Rest**: Azure Storage encryption
- **PII Handling**: Data masking, controlled access
- **Secrets Management**: Azure Key Vault

### Compliance
- **Audit Logging**: All operations logged
- **Data Retention**: Configurable retention policies
- **Access Controls**: RBAC at service level

## Disaster Recovery

- **Backup Strategy**: Daily backups to geo-redundant storage
- **RTO Target**: 4 hours
- **RPO Target**: 1 hour
- **Failover**: Automated regional failover
- **Testing**: Monthly DR drills

## Cost Optimization

- **Reserved Instances**: For predictable workloads
- **Spot Instances**: For non-critical batch processing
- **Autoscaling**: Scale down during off-peak hours
- **Storage Tiering**: Archive old documents
- **Cost Monitoring**: Azure Cost Management alerts
