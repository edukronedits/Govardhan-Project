"""
Document Processor - Azure Databricks notebook for bill processing
Handles OCR, text preprocessing, entity extraction
"""

# Databricks notebook source

# COMMAND --------

# Install required packages
%pip install azure-ai-formrecognizer azure-identity python-docx pillow openpyxl pandas

# COMMAND --------

from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.identity import DefaultAzureCredential
from azure.storage.blob import BlobClient
import pandas as pd
import json
from datetime import datetime
import re

# COMMAND --------

# Initialize Azure clients
endpoint = dbutils.secrets.get(scope="bill-processing", key="document-intelligence-endpoint")
key = dbutils.secrets.get(scope="bill-processing", key="document-intelligence-key")
storage_conn = dbutils.secrets.get(scope="bill-processing", key="storage-connection")

client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))

# COMMAND --------

def ocr_extract(document_path: str) -> dict:
    """
    Extract text and tables from document using Azure Document Intelligence
    
    Args:
        document_path: Path to document in blob storage
    
    Returns:
        Dictionary with extracted text, tables, and confidence scores
    """
    
    try:
        # Download document from blob
        blob_client = BlobClient.from_connection_string(
            storage_conn,
            "raw-documents",
            document_path.split("/")[-1]
        )
        
        with open("/tmp/document.pdf", "wb") as f:
            download_stream = blob_client.download_blob()
            f.write(download_stream.readall())
        
        # Run OCR with Form Recognizer
        with open("/tmp/document.pdf", "rb") as f:
            poller = client.begin_analyze_document("prebuilt-invoice", f)
        
        result = poller.result()
        
        # Extract structured fields
        extracted = {
            "vendor_name": result.fields.get("VendorName", {}).value if result.fields.get("VendorName") else None,
            "invoice_id": result.fields.get("InvoiceId", {}).value if result.fields.get("InvoiceId") else None,
            "invoice_date": str(result.fields.get("InvoiceDate", {}).value) if result.fields.get("InvoiceDate") else None,
            "due_date": str(result.fields.get("DueDate", {}).value) if result.fields.get("DueDate") else None,
            "total_amount": float(result.fields.get("InvoiceTotal", {}).value) if result.fields.get("InvoiceTotal") else None,
            "raw_text": result.content,
            "pages": len(result.pages),
            "confidence_scores": {}
        }
        
        # Collect confidence scores
        for field_name, field_value in result.fields.items():
            if hasattr(field_value, "confidence"):
                extracted["confidence_scores"][field_name] = field_value.confidence
        
        return extracted
    
    except Exception as e:
        print(f"Error in OCR extraction: {str(e)}")
        raise

# COMMAND --------

def preprocess_text(text: str) -> str:
    """
    Clean and normalize extracted text
    
    Args:
        text: Raw extracted text
    
    Returns:
        Cleaned text
    """
    
    # Remove extra whitespace
    text = re.sub(r"\s+", " ", text)
    
    # Remove special characters but keep numbers and basic punctuation
    text = re.sub(r"[^\w\s\.\,\$\-\/\(\)]", "", text)
    
    # Convert to lowercase for processing
    text = text.lower()
    
    return text.strip()

# COMMAND --------

def extract_line_items(raw_text: str) -> list:
    """
    Extract line items from invoice text
    
    Args:
        raw_text: Preprocessed text from OCR
    
    Returns:
        List of line item dictionaries
    """
    
    line_items = []
    
    # Pattern to match line items: Description, Quantity, Unit Price, Total
    pattern = r"(.+?)\s+(\d+\.?\d*)\s+\$?([\d,\.]+)\s+\$?([\d,\.]+)"
    
    matches = re.finditer(pattern, raw_text)
    
    for match in matches:
        line_item = {
            "description": match.group(1).strip(),
            "quantity": float(match.group(2)),
            "unit_price": float(match.group(3).replace(",", "")),
            "total": float(match.group(4).replace(",", "")),
            "extraction_confidence": 0.85  # Placeholder
        }
        line_items.append(line_item)
    
    return line_items

# COMMAND --------

def calculate_confidence_scores(extracted_data: dict) -> dict:
    """
    Calculate overall confidence scores for extracted data
    
    Args:
        extracted_data: Dictionary of extracted information
    
    Returns:
        Enhanced dictionary with confidence metrics
    """
    
    field_confidences = extracted_data.get("confidence_scores", {})
    
    overall_confidence = (
        sum(field_confidences.values()) / len(field_confidences) 
        if field_confidences else 0.5
    )
    
    extracted_data["overall_confidence"] = overall_confidence
    extracted_data["requires_manual_review"] = overall_confidence < 0.75
    
    return extracted_data

# COMMAND --------

def process_document_pipeline(ingestion_id: str, document_path: str) -> dict:
    """
    End-to-end document processing pipeline
    
    Args:
        ingestion_id: Unique document identifier
        document_path: Path to document in blob storage
    
    Returns:
        Dictionary with fully processed document data
    """
    
    print(f"Starting document processing for {ingestion_id}")
    
    # Step 1: OCR Extraction
    print("Step 1: OCR Extraction...")
    ocr_results = ocr_extract(document_path)
    
    # Step 2: Text Preprocessing
    print("Step 2: Text Preprocessing...")
    cleaned_text = preprocess_text(ocr_results["raw_text"])
    
    # Step 3: Entity Extraction
    print("Step 3: Entity Extraction...")
    line_items = extract_line_items(cleaned_text)
    
    # Step 4: Calculate Confidence
    print("Step 4: Confidence Scoring...")
    ocr_results = calculate_confidence_scores(ocr_results)
    
    # Compile final output
    processed_output = {
        "ingestion_id": ingestion_id,
        "document_path": document_path,
        "processing_timestamp": datetime.utcnow().isoformat(),
        "extracted_data": {
            "vendor_name": ocr_results.get("vendor_name"),
            "invoice_id": ocr_results.get("invoice_id"),
            "invoice_date": ocr_results.get("invoice_date"),
            "due_date": ocr_results.get("due_date"),
            "total_amount": ocr_results.get("total_amount")
        },
        "line_items": line_items,
        "quality_metrics": {
            "overall_confidence": ocr_results.get("overall_confidence"),
            "requires_manual_review": ocr_results.get("requires_manual_review"),
            "pages_processed": ocr_results.get("pages")
        },
        "processing_stage": "document_processed"
    }
    
    print(f"Document processing completed for {ingestion_id}")
    return processed_output

# COMMAND --------

# MAIN EXECUTION
# This would be triggered by Service Bus message in production

# Example execution:
# result = process_document_pipeline(
#     ingestion_id="doc-12345",
#     document_path="2024/doc-12345.pdf"
# )

# Save results to storage
# result_df = spark.createDataFrame([result])
# result_df.write.mode("append").parquet("dbfs:/mnt/processed-documents/")
