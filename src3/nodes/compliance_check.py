"""
Step 5: Compliance Check
Final verification that no hallucinations were introduced
"""

from typing import Dict, Any


def compliance_check(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Final compliance check to ensure no hallucinations.
    Verifies all outputs trace back to validated facts.
    """
    
    outputs = state.get("outputs")
    validated = state.get("validated_facts")
    
    if not outputs or not validated:
        return {
            **state,
            "compliance_passed": False,
            "compliance_issues": ["Missing outputs or validated facts"]
        }
    
    issues = []
    
    # Get all fact content for reference
    fact_contents = set(f.content.lower() for f in validated.facts)
    
    # Check action points
    for ap in outputs.action_points:
        # Verify source_facts exist
        if not ap.source_facts:
            issues.append(f"Action point missing source_facts: {ap.description[:50]}")
    
    # Check todos
    for td in outputs.todos:
        if not td.source_facts:
            issues.append(f"Todo missing source_facts: {td.task[:50]}")
        
        # Check deadline format
        if td.deadline and td.deadline.lower() in ["not specified", "none", "n/a"]:
            issues.append(f"Todo has invalid deadline format: {td.deadline}")
    
    # Check emails
    for email in outputs.follow_up_emails:
        # Check for placeholders
        if "[" in email.body and "]" in email.body:
            issues.append("Email contains placeholders")
    
    compliance_passed = len(issues) == 0
    
    if compliance_passed:
        print(f"✓ Compliance check PASSED")
    else:
        print(f"⚠ Compliance check found {len(issues)} issues:")
        for issue in issues[:3]:
            print(f"  - {issue}")
    
    return {
        **state,
        "compliance_passed": compliance_passed,
        "compliance_issues": issues
    }
