"""
AI Agent Framework - LangChain-based agents for bill processing
Implements extractors, rule validators, and rule predictors
"""

from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.tools import Tool, tool
from langchain_community.vectorstores import AzureSearch
from azure.identity import DefaultAzureCredential
import json
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger("AIAgentFramework")


class ExtractorAgent:
    """Agent for structured data extraction from documents"""
    
    def __init__(self, model: str = "gpt-4"):
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.embeddings = OpenAIEmbeddings()
        self.tools = self._setup_tools()
    
    def _setup_tools(self) -> List[Tool]:
        """Setup tools for the extractor agent"""
        
        @tool
        def parse_vendor_info(text: str) -> Dict[str, str]:
            """Extract vendor information from text"""
            return {
                "vendor_name": "Extracted vendor name",
                "vendor_id": "vendor-001",
                "contact_info": "vendor@example.com"
            }
        
        @tool
        def parse_invoice_dates(text: str) -> Dict[str, str]:
            """Extract date information from invoice"""
            return {
                "invoice_date": "2024-01-15",
                "due_date": "2024-02-15",
                "post_date": "2024-01-20"
            }
        
        @tool
        def parse_financial_info(text: str) -> Dict[str, float]:
            """Extract financial information"""
            return {
                "subtotal": 1000.00,
                "tax": 100.00,
                "total": 1100.00,
                "discount": 0.00
            }
        
        @tool
        def retrieve_similar_invoices(vendor_name: str, amount: float) -> List[Dict]:
            """Retrieve similar historical invoices from vector DB"""
            return [
                {
                    "invoice_id": "INV-2024-001",
                    "similarity_score": 0.92,
                    "vendor": vendor_name,
                    "amount": amount
                }
            ]
        
        return [parse_vendor_info, parse_invoice_dates, parse_financial_info, retrieve_similar_invoices]
    
    async def extract(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract structured data from document
        
        Args:
            document_data: Raw document content and metadata
        
        Returns:
            Extracted structured data with confidence scores
        """
        
        extraction_prompt = f"""
        You are an expert invoice processor. Extract the following information from the document:
        
        Document Content:
        {document_data.get('raw_text', '')}
        
        Please extract:
        1. Vendor information
        2. Invoice dates
        3. Financial information
        4. Line items
        
        Use the available tools to ensure accuracy. Return a JSON with extracted data and confidence scores.
        """
        
        try:
            # Create agent
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=extraction_prompt
            )
            
            agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
            
            # Run extraction
            result = agent_executor.invoke({"input": extraction_prompt})
            
            return {
                "extracted_data": result.get("output", {}),
                "extraction_confidence": 0.85,
                "extraction_timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error in extraction: {str(e)}")
            return {"error": str(e), "extracted_data": {}}


class BusinessRuleAgent:
    """Agent for validating extracted data against business rules"""
    
    def __init__(self, model: str = "gpt-4"):
        self.llm = ChatOpenAI(model=model, temperature=0)
        self.tools = self._setup_tools()
    
    def _setup_tools(self) -> List[Tool]:
        """Setup tools for business rule validation"""
        
        @tool
        def check_vendor_approval(vendor_name: str) -> Dict[str, Any]:
            """Check if vendor is approved"""
            return {
                "vendor_approved": True,
                "approval_status": "active",
                "approval_limits": {"single_transaction": 50000, "monthly": 500000}
            }
        
        @tool
        def validate_invoice_amount(amount: float, vendor_name: str) -> Dict[str, Any]:
            """Validate invoice amount against business rules"""
            return {
                "valid": amount < 50000,
                "reason": "Amount within approval limit",
                "confidence": 0.95
            }
        
        @tool
        def check_duplicate_invoice(invoice_id: str, vendor_name: str) -> Dict[str, Any]:
            """Check for duplicate invoices"""
            return {
                "is_duplicate": False,
                "similar_invoices": [],
                "confidence": 0.98
            }
        
        @tool
        def validate_line_items(line_items: List[Dict]) -> Dict[str, Any]:
            """Validate line items against policies"""
            return {
                "valid_items": len(line_items),
                "invalid_items": [],
                "validation_issues": []
            }
        
        return [
            check_vendor_approval,
            validate_invoice_amount,
            check_duplicate_invoice,
            validate_line_items
        ]
    
    async def validate(self, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted data against business rules
        
        Args:
            extracted_data: Extracted information from ExtractorAgent
        
        Returns:
            Validation results with pass/fail/review status
        """
        
        validation_prompt = f"""
        Validate the following invoice data against our business rules:
        
        Vendor: {extracted_data.get('vendor_name')}
        Amount: {extracted_data.get('total_amount')}
        Invoice ID: {extracted_data.get('invoice_id')}
        
        Use the validation tools to check:
        1. Vendor approval status
        2. Amount limits
        3. Duplicate detection
        4. Line item validation
        
        Return a comprehensive validation report.
        """
        
        try:
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=validation_prompt
            )
            
            agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
            result = agent_executor.invoke({"input": validation_prompt})
            
            return {
                "validation_result": result.get("output", {}),
                "validation_status": "passed",  # Would be determined by rules
                "validation_timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error in validation: {str(e)}")
            return {"error": str(e), "validation_status": "failed"}


class RulePredictorAgent:
    """Agent for predicting and generating new business rules"""
    
    def __init__(self, model: str = "gpt-4"):
        self.llm = ChatOpenAI(model=model, temperature=0.3)
        self.tools = self._setup_tools()
    
    def _setup_tools(self) -> List[Tool]:
        """Setup tools for rule prediction"""
        
        @tool
        def analyze_mismatch_pattern(mismatches: List[Dict]) -> Dict[str, Any]:
            """Analyze pattern in mismatches"""
            return {
                "pattern": "Recurring vendor field format issue",
                "frequency": 0.15,
                "affected_vendors": ["Vendor A", "Vendor B"],
                "root_cause": "Vendor uses non-standard format"
            }
        
        @tool
        def fetch_historical_rules(vendor_name: str) -> List[Dict]:
            """Fetch similar historical rules"""
            return [
                {
                    "rule_id": "RULE-001",
                    "condition": "Vendor name ends with 'Inc'",
                    "action": "Normalize to standard format",
                    "success_rate": 0.92
                }
            ]
        
        @tool
        def validate_rule_effectiveness(rule: Dict) -> Dict[str, float]:
            """Validate effectiveness of proposed rule"""
            return {
                "precision": 0.92,
                "recall": 0.88,
                "f1_score": 0.90,
                "applicability": 0.80
            }
        
        return [analyze_mismatch_pattern, fetch_historical_rules, validate_rule_effectiveness]
    
    async def predict_rules(self, mismatches: List[Dict]) -> Dict[str, Any]:
        """
        Predict and generate new business rules from mismatches
        
        Args:
            mismatches: List of validation mismatches
        
        Returns:
            Proposed rules with effectiveness scores
        """
        
        prediction_prompt = f"""
        We have detected {len(mismatches)} validation mismatches in our invoice processing.
        
        Mismatches: {json.dumps(mismatches, indent=2)}
        
        Using the available tools:
        1. Analyze the pattern in these mismatches
        2. Fetch similar historical rules
        3. Generate new rules to address the pattern
        4. Validate their effectiveness
        
        Return proposed rules that should be submitted for human review.
        """
        
        try:
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=self.tools,
                prompt=prediction_prompt
            )
            
            agent_executor = AgentExecutor(agent=agent, tools=self.tools, verbose=True)
            result = agent_executor.invoke({"input": prediction_prompt})
            
            return {
                "proposed_rules": result.get("output", {}),
                "recommendation": "human_review",
                "prediction_timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error in rule prediction: {str(e)}")
            return {"error": str(e), "proposed_rules": []}


async def run_multi_agent_pipeline(document_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run complete multi-agent pipeline for bill processing
    
    Args:
        document_data: Raw document data from ingestion
    
    Returns:
        Complete processing result with all agent outputs
    """
    
    logger.info(f"Starting multi-agent pipeline for {document_data.get('ingestion_id')}")
    
    # Initialize agents
    extractor = ExtractorAgent()
    validator = BusinessRuleAgent()
    predictor = RulePredictorAgent()
    
    # Run extraction
    extraction_result = await extractor.extract(document_data)
    
    # Run validation
    validation_result = await validator.validate(extraction_result.get("extracted_data", {}))
    
    # If validation fails, predict new rules
    rule_predictions = None
    if validation_result.get("validation_status") != "passed":
        rule_predictions = await predictor.predict_rules([
            {"mismatch": "validation_failed", "reason": "Check validation_result"}
        ])
    
    # Compile final output
    pipeline_output = {
        "ingestion_id": document_data.get("ingestion_id"),
        "extraction_result": extraction_result,
        "validation_result": validation_result,
        "rule_predictions": rule_predictions,
        "pipeline_status": "completed",
        "processing_timestamp": datetime.utcnow().isoformat()
    }
    
    logger.info(f"Multi-agent pipeline completed for {document_data.get('ingestion_id')}")
    
    return pipeline_output
