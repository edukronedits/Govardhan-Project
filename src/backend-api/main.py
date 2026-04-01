"""
Backend API - FastAPI application for bill processing system
"""

from fastapi import FastAPI, HTTPException, Depends, status, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import uuid4
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Bill Processing System API",
    version="1.0.0",
    description="REST API for AI-powered bill processing"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Pydantic Models =====

class DocumentMetadata(BaseModel):
    """Metadata for a document"""
    vendor_name: str
    bill_date: str
    bill_amount: float
    source: Optional[str] = "api"


class LineItem(BaseModel):
    """Invoice line item"""
    description: str
    quantity: float
    unit_price: float
    total: float
    sku: Optional[str] = None


class ExtractionResult(BaseModel):
    """Document extraction result"""
    ingestion_id: str
    vendor_name: Optional[str]
    invoice_id: Optional[str]
    invoice_date: Optional[str]
    due_date: Optional[str]
    total_amount: Optional[float]
    line_items: List[LineItem] = []
    overall_confidence: float
    requires_manual_review: bool
    extraction_timestamp: str


class ValidationResult(BaseModel):
    """Rule validation result"""
    overall_status: str = Field(..., description="passed|failed|requires_review")
    passed_rules: int
    failed_rules: int
    review_required_rules: int
    rule_results: List[Dict[str, Any]]
    validation_timestamp: str


class DocumentProcessingResult(BaseModel):
    """Complete document processing result"""
    ingestion_id: str
    extraction_result: ExtractionResult
    validation_result: ValidationResult
    status: str = Field(..., description="completed|failed|pending")
    processing_timestamp: str


class BusinessRule(BaseModel):
    """Business rule definition"""
    rule_id: str
    name: str
    rule_type: str = Field(..., description="deterministic|probabilistic|ai_inferred")
    condition: str
    action: str
    priority: int
    enabled: bool
    confidence_threshold: float = 0.8


class BulkIngestionRequest(BaseModel):
    """Request for bulk document ingestion"""
    batch_id: str
    documents: List[DocumentMetadata]
    priority: int = 5


# ===== In-Memory Storage (replace with DB in production) =====

documents_store: Dict[str, DocumentProcessingResult] = {}
rules_store: Dict[str, BusinessRule] = {}
extraction_queue: List[str] = []


# ===== Health Check =====

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "bill-processing-api"
    }


# ===== Document Endpoints =====

@app.post("/documents", response_model=Dict[str, Any], status_code=202)
async def upload_document(metadata: DocumentMetadata):
    """
    Upload and ingest a new document for processing
    
    Returns:
        ingestion_id: Unique identifier for tracking
        status: Initial processing status
    """
    
    try:
        ingestion_id = str(uuid4())
        
        logger.info(f"Document ingested: {ingestion_id} from {metadata.vendor_name}")
        
        # In production, this would queue the document for processing
        extraction_queue.append(ingestion_id)
        
        return {
            "ingestion_id": ingestion_id,
            "status": "ingested",
            "message": "Document queued for processing",
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail="Error processing document")


@app.get("/documents/{ingestion_id}", response_model=DocumentProcessingResult)
async def get_document(ingestion_id: str):
    """
    Retrieve document processing result
    
    Args:
        ingestion_id: Unique document identifier
    
    Returns:
        Complete processing result with extractions and validations
    """
    
    if ingestion_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    return documents_store[ingestion_id]


@app.get("/documents", response_model=List[DocumentProcessingResult])
async def list_documents(
    skip: int = 0,
    limit: int = 50,
    vendor_name: Optional[str] = None,
    status: Optional[str] = None
):
    """
    List documents with filtering
    
    Args:
        skip: Pagination offset
        limit: Pagination limit
        vendor_name: Filter by vendor
        status: Filter by processing status
    
    Returns:
        List of document processing results
    """
    
    results = list(documents_store.values())
    
    if vendor_name:
        results = [
            r for r in results 
            if r.extraction_result.vendor_name == vendor_name
        ]
    
    if status:
        results = [r for r in results if r.status == status]
    
    return results[skip:skip + limit]


@app.post("/documents/{ingestion_id}/review")
async def submit_review(ingestion_id: str, review_data: Dict[str, Any]):
    """
    Submit manual review for a document
    
    Args:
        ingestion_id: Document identifier
        review_data: Reviewer corrections and validations
    
    Returns:
        Updated document with review data
    """
    
    if ingestion_id not in documents_store:
        raise HTTPException(status_code=404, detail="Document not found")
    
    doc = documents_store[ingestion_id]
    
    logger.info(f"Review submitted for document: {ingestion_id}")
    
    return {
        "ingestion_id": ingestion_id,
        "status": "reviewed",
        "review_timestamp": datetime.utcnow().isoformat(),
        "message": "Review data saved successfully"
    }


# ===== Rule Endpoints =====

@app.post("/rules", response_model=BusinessRule, status_code=201)
async def create_rule(rule: BusinessRule):
    """
    Create a new business rule
    
    Args:
        rule: Rule definition
    
    Returns:
        Created rule with metadata
    """
    
    if rule.rule_id in rules_store:
        raise HTTPException(status_code=409, detail="Rule ID already exists")
    
    rules_store[rule.rule_id] = rule
    
    logger.info(f"Rule created: {rule.rule_id}")
    
    return rule


@app.get("/rules", response_model=List[BusinessRule])
async def list_rules(enabled_only: bool = False):
    """
    List all business rules
    
    Args:
        enabled_only: Return only enabled rules
    
    Returns:
        List of business rules
    """
    
    rules = list(rules_store.values())
    
    if enabled_only:
        rules = [r for r in rules if r.enabled]
    
    return rules


@app.get("/rules/{rule_id}", response_model=BusinessRule)
async def get_rule(rule_id: str):
    """Get a specific rule"""
    
    if rule_id not in rules_store:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return rules_store[rule_id]


@app.put("/rules/{rule_id}", response_model=BusinessRule)
async def update_rule(rule_id: str, rule: BusinessRule):
    """Update an existing rule"""
    
    if rule_id not in rules_store:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rules_store[rule_id] = rule
    
    logger.info(f"Rule updated: {rule_id}")
    
    return rule


@app.delete("/rules/{rule_id}", status_code=204)
async def delete_rule(rule_id: str):
    """Delete a rule"""
    
    if rule_id not in rules_store:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    del rules_store[rule_id]
    
    logger.info(f"Rule deleted: {rule_id}")


# ===== Batch Operations =====

@app.post("/batch/ingest", status_code=202)
async def batch_ingest(batch_request: BulkIngestionRequest):
    """
    Ingest multiple documents in batch
    
    Args:
        batch_request: Batch ingestion request with multiple documents
    
    Returns:
        Batch processing status with ingestion IDs
    """
    
    ingestion_ids = []
    
    for doc in batch_request.documents:
        ingestion_id = str(uuid4())
        ingestion_ids.append(ingestion_id)
        extraction_queue.append(ingestion_id)
    
    logger.info(f"Batch ingestion queued: {batch_request.batch_id} with {len(ingestion_ids)} documents")
    
    return {
        "batch_id": batch_request.batch_id,
        "ingestion_ids": ingestion_ids,
        "total_documents": len(ingestion_ids),
        "status": "queued",
        "timestamp": datetime.utcnow().isoformat()
    }


# ===== Analytics Endpoints =====

@app.get("/analytics/summary")
async def get_analytics_summary():
    """Get processing analytics and metrics"""
    
    total_docs = len(documents_store)
    passed = sum(1 for d in documents_store.values() if d.validation_result.overall_status == "passed")
    failed = sum(1 for d in documents_store.values() if d.validation_result.overall_status == "failed")
    review = sum(1 for d in documents_store.values() if d.validation_result.overall_status == "requires_review")
    
    return {
        "total_documents_processed": total_docs,
        "passed_validations": passed,
        "failed_validations": failed,
        "requires_review": review,
        "accuracy_rate": passed / total_docs if total_docs > 0 else 0,
        "total_rules": len(rules_store),
        "enabled_rules": sum(1 for r in rules_store.values() if r.enabled),
        "queued_documents": len(extraction_queue),
        "timestamp": datetime.utcnow().isoformat()
    }


# ===== Error Handlers =====

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {str(exc)}")
    return {
        "error": "Internal server error",
        "detail": str(exc),
        "timestamp": datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
