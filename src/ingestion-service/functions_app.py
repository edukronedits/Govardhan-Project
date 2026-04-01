"""
Ingestion Service - Azure Functions for bill ingestion
Handles multi-source ingestion with validation and enrichment
"""

import azure.functions as func
import json
from datetime import datetime
from typing import Dict, Any
import logging
from azure.storage.blob import BlobClient
from azure.servicebus import ServiceBusClient, ServiceBusMessage
import uuid

logger = logging.getLogger("IngestionService")

# Initialize clients (these should be injected via dependency injection)
SERVICE_BUS_CONNECTION_STRING = "${SERVICE_BUS_CONNECTION_STRING}"
STORAGE_ACCOUNT_CONNECTION_STRING = "${STORAGE_ACCOUNT_CONNECTION_STRING}"


def validate_bill_format(data: Dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate bill metadata and format"""
    errors = []
    
    required_fields = ["vendor_name", "bill_date", "bill_amount"]
    for field in required_fields:
        if field not in data:
            errors.append(f"Missing required field: {field}")
    
    # Validate date format
    if "bill_date" in data:
        try:
            datetime.fromisoformat(data["bill_date"])
        except (ValueError, TypeError):
            errors.append("Invalid bill_date format (expected ISO 8601)")
    
    # Validate amount is numeric
    if "bill_amount" in data:
        try:
            float(data["bill_amount"])
        except (ValueError, TypeError):
            errors.append("bill_amount must be numeric")
    
    return len(errors) == 0, errors


def enrich_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add metadata to incoming data"""
    return {
        **data,
        "ingestion_id": str(uuid.uuid4()),
        "ingestion_timestamp": datetime.utcnow().isoformat(),
        "source": data.get("source", "api"),
        "status": "ingested",
        "processing_stage": "awaiting_document_processing"
    }


async def send_to_service_bus(message_data: Dict[str, Any], topic: str = "bill-processing"):
    """Send enqueued message to Service Bus"""
    try:
        async with ServiceBusClient.from_connection_string(
            SERVICE_BUS_CONNECTION_STRING
        ) as client:
            sender = client.get_topic_sender(topic)
            async with sender:
                message = ServiceBusMessage(
                    json.dumps(message_data),
                    correlation_id=message_data.get("ingestion_id")
                )
                await sender.send_messages(message)
                logger.info(f"Message sent to Service Bus: {message_data['ingestion_id']}")
    except Exception as e:
        logger.error(f"Error sending to Service Bus: {str(e)}")
        raise


async def store_document(document_content: bytes, ingestion_id: str) -> str:
    """Store raw document in blob storage"""
    try:
        container_name = "raw-documents"
        blob_name = f"{datetime.utcnow().year}/{ingestion_id}.pdf"
        
        blob_client = BlobClient.from_connection_string(
            STORAGE_ACCOUNT_CONNECTION_STRING,
            container_name,
            blob_name
        )
        await blob_client.upload_blob(document_content, overwrite=True)
        logger.info(f"Document stored: {blob_name}")
        return blob_name
    except Exception as e:
        logger.error(f"Error storing document: {str(e)}")
        raise


@func.route_with_auth("IngestionHTTP", route="documents", methods=["POST"], auth_level=func.AuthLevel.FUNCTION)
async def ingestion_http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    """
    HTTP trigger for bill ingestion via API
    Expected JSON: { vendor_name, bill_date, bill_amount, ... }
    Optional: Raw document file in multipart/form-data
    """
    try:
        # Parse JSON body
        req_body = req.get_json()
        
        # Validate format
        is_valid, errors = validate_bill_format(req_body)
        if not is_valid:
            return func.HttpResponse(
                json.dumps({"error": "Validation failed", "details": errors}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Enrich with metadata
        enriched_data = enrich_metadata(req_body)
        
        # Store raw document if provided
        if "document_content" in req.files:
            document = req.files["document_content"]
            blob_url = await store_document(
                document.read(),
                enriched_data["ingestion_id"]
            )
            enriched_data["document_blob_url"] = blob_url
        
        # Send to Service Bus for async processing
        await send_to_service_bus(enriched_data)
        
        return func.HttpResponse(
            json.dumps({
                "status": "success",
                "ingestion_id": enriched_data["ingestion_id"],
                "message": "Bill ingested successfully"
            }),
            status_code=202,
            mimetype="application/json"
        )
    
    except Exception as e:
        logger.error(f"Error in ingestion_http_trigger: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            mimetype="application/json"
        )


@func.service_bus_topic_trigger(
    arg_name="msg",
    connection="ServiceBusConnection",
    topic_name="bill-ingestion",
    subscription_name="batch-processor"
)
async def batch_ingestion_trigger(msg: func.InputStream):
    """Service Bus trigger for batch processing requests"""
    try:
        batch_request = json.loads(msg.read().decode("utf-8"))
        
        logger.info(f"Processing batch ingestion: {batch_request.get('batch_id')}")
        
        # Enrich each document
        documents = batch_request.get("documents", [])
        enriched_docs = [
            enrich_metadata(doc) for doc in documents
            if validate_bill_format(doc)[0]
        ]
        
        # Send to processing topic
        for doc in enriched_docs:
            await send_to_service_bus(doc)
        
        logger.info(f"Batch ingestion completed: {len(enriched_docs)} documents processed")
    
    except Exception as e:
        logger.error(f"Error in batch_ingestion_trigger: {str(e)}")
        raise


@func.timer_trigger(
    arg_name="myTimer",
    schedule="0 0 * * * *"  # Daily at midnight
)
def health_check_trigger(myTimer: func.TimerRequest):
    """Periodic health check and cleanup"""
    if myTimer.past_due:
        logger.warning("Health check running behind schedule")
    
    logger.info("Ingestion service health check completed")
