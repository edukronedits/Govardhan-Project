"""
Business Rule Engine - Executes deterministic, probabilistic, and AI-inferred rules
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger("RuleEngine")


class RuleType(Enum):
    """Types of business rules"""
    DETERMINISTIC = "deterministic"
    PROBABILISTIC = "probabilistic"
    AI_INFERRED = "ai_inferred"


class RuleStatus(Enum):
    """Rule execution status"""
    PASSED = "passed"
    FAILED = "failed"
    REQUIRES_REVIEW = "requires_review"
    PROCESSING = "processing"


@dataclass
class Rule:
    """Business rule definition"""
    rule_id: str
    name: str
    rule_type: RuleType
    condition: str
    action: str
    priority: int  # Higher = executed first
    enabled: bool
    confidence_threshold: float = 0.8
    created_at: str = None
    created_by: str = None


@dataclass
class RuleExecutionResult:
    """Result of rule execution"""
    rule_id: str
    status: RuleStatus
    passed: bool
    confidence: float
    message: str
    execution_time_ms: float
    affected_fields: List[str]


class RuleEngine:
    """Business rule execution engine"""
    
    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.execution_log: List[Dict[str, Any]] = []
    
    def register_rule(self, rule: Rule) -> bool:
        """Register a new rule"""
        if rule.rule_id in self.rules:
            logger.warning(f"Rule {rule.rule_id} already registered, overwriting")
        
        self.rules[rule.rule_id] = rule
        logger.info(f"Rule registered: {rule.rule_id}")
        return True
    
    def unregister_rule(self, rule_id: str) -> bool:
        """Unregister a rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info(f"Rule unregistered: {rule_id}")
            return True
        return False
    
    def _evaluate_deterministic_rule(self, rule: Rule, data: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Evaluate a deterministic rule
        
        Returns: (passed, confidence)
        """
        try:
            # Simple condition evaluation - in production this would use a DSL
            # For now, implementing basic pattern matching
            
            result = eval(rule.condition, {"data": data, "len": len, "str": str})
            confidence = 1.0 if result else 0.0
            
            return result, confidence
        
        except Exception as e:
            logger.error(f"Error evaluating deterministic rule {rule.rule_id}: {str(e)}")
            return False, 0.0
    
    def _evaluate_probabilistic_rule(self, rule: Rule, data: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Evaluate a probabilistic rule using fuzzy matching
        
        Returns: (passed, confidence)
        """
        # Placeholder for probabilistic logic (fuzzy matching, thresholds, etc.)
        confidence = 0.75
        passed = confidence >= rule.confidence_threshold
        
        return passed, confidence
    
    def _evaluate_ai_inferred_rule(self, rule: Rule, data: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Evaluate an AI-inferred rule using LLM or ML model
        
        Returns: (passed, confidence)
        """
        # Placeholder for AI rule evaluation
        # In production, this would call the AI agent framework
        confidence = 0.82
        passed = confidence >= rule.confidence_threshold
        
        return passed, confidence
    
    def execute_rule(self, rule: Rule, data: Dict[str, Any]) -> RuleExecutionResult:
        """Execute a single rule against data"""
        
        import time
        start_time = time.time()
        
        try:
            # Select evaluation method based on rule type
            if rule.rule_type == RuleType.DETERMINISTIC:
                passed, confidence = self._evaluate_deterministic_rule(rule, data)
            elif rule.rule_type == RuleType.PROBABILISTIC:
                passed, confidence = self._evaluate_probabilistic_rule(rule, data)
            elif rule.rule_type == RuleType.AI_INFERRED:
                passed, confidence = self._evaluate_ai_inferred_rule(rule, data)
            else:
                passed, confidence = False, 0.0
            
            # Determine status
            if confidence < rule.confidence_threshold:
                status = RuleStatus.REQUIRES_REVIEW
            elif passed:
                status = RuleStatus.PASSED
            else:
                status = RuleStatus.FAILED
            
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            result = RuleExecutionResult(
                rule_id=rule.rule_id,
                status=status,
                passed=passed,
                confidence=confidence,
                message=rule.action,
                execution_time_ms=execution_time,
                affected_fields=[]  # Would be populated based on rule
            )
            
            # Log execution
            self.execution_log.append({
                "rule_id": rule.rule_id,
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            })
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing rule {rule.rule_id}: {str(e)}")
            return RuleExecutionResult(
                rule_id=rule.rule_id,
                status=RuleStatus.FAILED,
                passed=False,
                confidence=0.0,
                message=f"Error: {str(e)}",
                execution_time_ms=(time.time() - start_time) * 1000,
                affected_fields=[]
            )
    
    def execute_rules(self, data: Dict[str, Any], 
                      rule_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Execute all relevant rules for given data
        
        Args:
            data: Document data to validate
            rule_ids: Specific rule IDs to execute (None = all enabled rules)
        
        Returns:
            Validation result with all rule outcomes
        """
        
        # Select rules to execute
        rules_to_execute = []
        if rule_ids:
            rules_to_execute = [self.rules[rid] for rid in rule_ids if rid in self.rules]
        else:
            rules_to_execute = [r for r in self.rules.values() if r.enabled]
        
        # Sort by priority
        rules_to_execute.sort(key=lambda r: r.priority, reverse=True)
        
        # Execute rules
        execution_results = []
        passed_count = 0
        failed_count = 0
        review_count = 0
        
        for rule in rules_to_execute:
            result = self.execute_rule(rule, data)
            execution_results.append(result)
            
            if result.status == RuleStatus.PASSED:
                passed_count += 1
            elif result.status == RuleStatus.FAILED:
                failed_count += 1
            elif result.status == RuleStatus.REQUIRES_REVIEW:
                review_count += 1
        
        # Determine overall validation status
        overall_status = "passed"
        if failed_count > 0:
            overall_status = "failed"
        elif review_count > 0:
            overall_status = "requires_review"
        
        return {
            "overall_status": overall_status,
            "passed_rules": passed_count,
            "failed_rules": failed_count,
            "review_required_rules": review_count,
            "rule_results": [
                {
                    "rule_id": r.rule_id,
                    "status": r.status.value,
                    "passed": r.passed,
                    "confidence": r.confidence,
                    "message": r.message,
                    "execution_time_ms": r.execution_time_ms
                }
                for r in execution_results
            ],
            "validation_timestamp": datetime.utcnow().isoformat()
        }
    
    def validate_line_item(self, line_item: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual line item"""
        
        # Rules for line items
        line_item_validations = {
            "has_description": bool(line_item.get("description")),
            "has_quantity": line_item.get("quantity", 0) > 0,
            "has_unit_price": line_item.get("unit_price", 0) > 0,
            "amount_matches": abs(
                line_item.get("quantity", 0) * line_item.get("unit_price", 0) 
                - line_item.get("total", 0)
            ) < 0.01,
            "reasonable_amount": line_item.get("total", 0) < 999999.99
        }
        
        all_valid = all(line_item_validations.values())
        
        return {
            "line_item_valid": all_valid,
            "validations": line_item_validations,
            "validation_timestamp": datetime.utcnow().isoformat()
        }
    
    def detect_conflicts(self, rule_results: List[RuleExecutionResult]) -> List[Dict[str, Any]]:
        """Detect conflicts between rule outcomes"""
        
        conflicts = []
        
        # Simple conflict detection - in production this would be more sophisticated
        for i, rule1 in enumerate(rule_results):
            for rule2 in rule_results[i+1:]:
                if rule1.passed != rule2.passed and rule1.status != RuleStatus.REQUIRES_REVIEW:
                    conflicts.append({
                        "rule1_id": rule1.rule_id,
                        "rule2_id": rule2.rule_id,
                        "conflict_type": "contradictory_outcomes",
                        "resolution_required": True
                    })
        
        return conflicts


# Example usage
if __name__ == "__main__":
    # Initialize engine
    engine = RuleEngine()
    
    # Register sample rules
    rule1 = Rule(
        rule_id="RULE-001",
        name="Vendor Approval Check",
        rule_type=RuleType.DETERMINISTIC,
        condition="data.get('vendor_approved', False)",
        action="Vendor must be approved",
        priority=10,
        enabled=True
    )
    
    rule2 = Rule(
        rule_id="RULE-002",
        name="Amount Limit Check",
        rule_type=RuleType.PROBABILISTIC,
        condition="data.get('total_amount', 0) < 50000",
        action="Amount must be within approval limits",
        priority=9,
        enabled=True,
        confidence_threshold=0.75
    )
    
    engine.register_rule(rule1)
    engine.register_rule(rule2)
    
    # Execute rules
    test_data = {
        "vendor_approved": True,
        "total_amount": 25000,
        "invoice_id": "INV-001"
    }
    
    results = engine.execute_rules(test_data)
    print(json.dumps(results, indent=2))
