# Azure Durable Functions Orchestrator for Bill Processing

import azure.functions as func
import json
from datetime import datetime, timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger("Orchestrators")


class BillProcessorOrchestrator:
    """
    Orchestrates end-to-end bill processing workflow
    Manages: ingestion → document processing → AI extraction → rule validation → storage
    """
    
    @staticmethod
    def run_bill_processor_orchestrator(context):
        """
        Main orchestration workflow for bill processing
        
        Flow:
        1. Ingest document
        2. Extract text & structure (Document Intelligence)
        3. Process with AI agents
        4. Validate with business rules
        5. Store results
        6. Update dashboard
        """
        
        # Input data
        bill_data = context.get_input()
        
        # Step 1: Validate input
        validation_result = yield context.call_activity(
            'validate_bill_input',
            bill_data
        )
        
        if not validation_result['valid']:
            return {
                "status": "failed",
                "reason": validation_result['errors'],
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Step 2: Extract document
        extraction_result = yield context.call_activity(
            'extract_document',
            bill_data
        )
        
        # Step 3: Process with AI agents (parallel execution)
        ai_tasks = [
            context.call_activity('run_extractor_agent', extraction_result),
            context.call_activity('run_validator_agent', extraction_result),
        ]
        
        ai_results = yield context.task_all(ai_tasks)
        
        # Step 4: Apply business rules
        rule_results = yield context.call_activity(
            'execute_business_rules',
            {
                'extracted_data': ai_results[0],
                'validation_data': ai_results[1]
            }
        )
        
        # Step 5: Handle failures with retry
        if rule_results['validation_status'] == 'failed':
            # Retry with different parameters
            retry_policy = {
                'first_retry_interval': timedelta(seconds=5),
                'max_number_of_attempts': 3,
                'backoff_coefficient': 2.0
            }
            
            rule_results = yield context.call_activity_with_retry(
                'execute_business_rules_retry',
                retry_policy,
                rule_results
            )
        
        # Step 6: Store results
        storage_result = yield context.call_activity(
            'store_processing_results',
            {
                'bill_data': bill_data,
                'extraction_result': extraction_result,
                'ai_results': ai_results,
                'rule_results': rule_results
            }
        )
        
        # Step 7: Send notifications
        yield context.call_activity(
            'send_processing_notification',
            {
                'ingestion_id': bill_data.get('ingestion_id'),
                'status': 'completed',
                'storage_id': storage_result.get('document_id')
            }
        )
        
        return {
            "status": "completed",
            "ingestion_id": bill_data.get('ingestion_id'),
            "extraction_result": extraction_result,
            "rule_validation": rule_results,
            "storage_id": storage_result.get('document_id'),
            "timestamp": datetime.utcnow().isoformat()
        }


def validate_bill_input_activity(bill_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate input bill data"""
    try:
        required_fields = ['ingestion_id', 'vendor_name', 'bill_amount']
        missing_fields = [f for f in required_fields if f not in bill_data]
        
        if missing_fields:
            return {
                'valid': False,
                'errors': f'Missing fields: {missing_fields}'
            }
        
        return {'valid': True}
    
    except Exception as e:
        logger.error(f"Error validating input: {str(e)}")
        return {'valid': False, 'errors': str(e)}


def extract_document_activity(bill_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract text from document using Document Intelligence"""
    try:
        ingestion_id = bill_data.get('ingestion_id')
        logger.info(f"Extracting document: {ingestion_id}")
        
        # In production, this would call Azure Document Intelligence
        extraction_result = {
            'ingestion_id': ingestion_id,
            'raw_text': 'extracted text...',
            'confidence': 0.92,
            'extraction_timestamp': datetime.utcnow().isoformat()
        }
        
        return extraction_result
    
    except Exception as e:
        logger.error(f"Error extracting document: {str(e)}")
        raise


def run_extractor_agent_activity(extraction_result: Dict[str, Any]) -> Dict[str, Any]:
    """Run AI Extractor Agent"""
    try:
        logger.info(f"Running extractor agent for {extraction_result.get('ingestion_id')}")
        
        # In production, this would call the AI agent framework
        agent_result = {
            'vendor_name': extraction_result.get('vendor_name'),
            'invoice_id': 'INV-001',
            'invoice_date': '2024-01-15',
            'total_amount': 1000.00,
            'confidence': 0.88
        }
        
        return agent_result
    
    except Exception as e:
        logger.error(f"Error running extractor agent: {str(e)}")
        raise


def run_validator_agent_activity(extraction_result: Dict[str, Any]) -> Dict[str, Any]:
    """Run AI Business Rule Validator Agent"""
    try:
        logger.info(f"Running validator agent for {extraction_result.get('ingestion_id')}")
        
        # In production, this would call the rule validator agent
        validation_result = {
            'vendor_approved': True,
            'amount_within_limits': True,
            'no_duplicate': True,
            'validation_confidence': 0.95
        }
        
        return validation_result
    
    except Exception as e:
        logger.error(f"Error running validator agent: {str(e)}")
        raise


def execute_business_rules_activity(data: Dict[str, Any]) -> Dict[str, Any]:
    """Execute business rules"""
    try:
        logger.info("Executing business rules")
        
        # In production, this would call the rule engine
        rule_results = {
            'validation_status': 'passed',
            'passed_rules': 15,
            'failed_rules': 0,
            'rules_requiring_review': 2
        }
        
        return rule_results
    
    except Exception as e:
        logger.error(f"Error executing rules: {str(e)}")
        raise


def store_processing_results_activity(data: Dict[str, Any]) -> Dict[str, Any]:
    """Store all processing results"""
    try:
        logger.info("Storing processing results")
        
        # In production, this would store to databases
        # - SQL Server: Metadata
        # - Cosmos DB: Extracted data
        # - Blob Storage: Raw documents
        # - AI Search: Embeddings
        
        storage_result = {
            'document_id': 'doc-12345',
            'storage_status': 'stored',
            'storage_timestamp': datetime.utcnow().isoformat()
        }
        
        return storage_result
    
    except Exception as e:
        logger.error(f"Error storing results: {str(e)}")
        raise


def send_processing_notification_activity(notification_data: Dict[str, Any]) -> None:
    """Send processing completion notification"""
    try:
        ingestion_id = notification_data.get('ingestion_id')
        status = notification_data.get('status')
        
        logger.info(f"Sending notification for {ingestion_id}: {status}")
        
        # In production, this would send notifications via:
        # - Event Hub/Service Bus
        # - Email
        # - Webhooks
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        raise


# Register activities
def register_activities():
    """Register all activities with Azure Functions"""
    return {
        'validate_bill_input': validate_bill_input_activity,
        'extract_document': extract_document_activity,
        'run_extractor_agent': run_extractor_agent_activity,
        'run_validator_agent': run_validator_agent_activity,
        'execute_business_rules': execute_business_rules_activity,
        'store_processing_results': store_processing_results_activity,
        'send_processing_notification': send_processing_notification_activity,
    }
