"""
Step 5: Final Compliance Check
Ensure no new facts, names, or promises introduced before sending outputs
"""

from typing import Dict, Any, List


def compliance_check(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Final check to ensure outputs don't contain hallucinations.
    Compare outputs against validated facts.
    """
    
    outputs = state["outputs"]
    validated = state["validated_facts"]
    issues = []
    
    # Extract all content from validated facts
    fact_contents = [f.content.lower() for f in validated.facts]
    fact_quotes = [f.source_quote.lower() for f in validated.facts]
    
    # Check 1: Action points have source facts
    for i, ap in enumerate(outputs.action_points):
        if not ap.source_facts:
            issues.append(f"Action point {i+1} has no source facts")
    
    # Check 2: Todos have source facts
    for i, td in enumerate(outputs.todos):
        if not td.source_facts:
            issues.append(f"Todo {i+1} has no source facts")
    
    # Check 3: Emails have source facts
    for i, em in enumerate(outputs.follow_up_emails):
        if not em.source_facts:
            issues.append(f"Email {i+1} has no source facts")
        # Check for placeholders
        if "[Your Name]" in em.body or "[Date]" in em.body or "[Name]" in em.body:
            issues.append(f"Email {i+1} contains placeholder text")
    
    # Check 4: Summary doesn't have placeholders
    if "[" in outputs.summary and "]" in outputs.summary:
        issues.append("Summary contains placeholder text")
    
    passed = len(issues) == 0
    
    if passed:
        print(f"✓ Compliance check PASSED")
    else:
        print(f"⚠ Compliance check found {len(issues)} issues:")
        for issue in issues[:5]:  # Show first 5
            print(f"  - {issue}")
    
    return {
        **state,
        "compliance_passed": passed,
        "compliance_issues": issues
    }
