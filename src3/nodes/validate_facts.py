"""
Step 3: Validate Facts (Skills-Enhanced)
Uses VALIDATE_FACTS.md skill for quality control
"""

from typing import Dict, Any, List
from src3.models import ValidatedFact, ValidatedFacts, ExtractedFact
from src3.skill_loader import load_skill


def validate_facts(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extracted facts using rule-based checks.
    Applies the validation skill principles.
    """
    
    extracted = state["extracted_facts"]
    
    # Load skill for reference (used in validation logic)
    skill = load_skill("VALIDATE_FACTS")
    
    validated = []
    discarded = []
    discarded_reasons = []
    
    # Combine all facts
    all_facts = (
        extracted.decisions +
        extracted.action_items +
        extracted.deadlines +
        extracted.metrics
    )
    
    for fact in all_facts:
        is_valid, reason = _validate_single_fact(fact)
        
        if is_valid:
            validated.append(ValidatedFact(
                fact_type=fact.fact_type,
                content=fact.content,
                source_quote=fact.source_quote,
                confidence=fact.confidence,
                is_valid=True
            ))
        else:
            discarded.append(fact)
            discarded_reasons.append(reason)
    
    result = ValidatedFacts(
        facts=validated,
        discarded_count=len(discarded),
        discarded_reasons=discarded_reasons
    )
    
    print(f"✓ Validated facts: {len(validated)} kept, {len(discarded)} discarded")
    if discarded_reasons:
        print(f"  Discarded reasons:")
        for reason in discarded_reasons[:3]:  # Show first 3
            print(f"    - {reason}")
    
    return {
        **state,
        "validated_facts": result
    }


def _validate_single_fact(fact: ExtractedFact) -> tuple:
    """
    Validate a single fact.
    Returns (is_valid, reason_if_invalid)
    """
    
    content = fact.content.lower()
    source = fact.source_quote.lower()
    
    # Rule 1: Must have source quote
    if not fact.source_quote or len(fact.source_quote) < 5:
        return False, f"Missing source quote: {fact.content[:50]}"
    
    # Rule 2: No conditional language (but be careful not to reject commitments)
    # Only reject if the conditional is the main clause, not a side note
    conditional_patterns = [
        " if it fails",
        " if the test fails",
        " if needed",
        " might have to",
        " may need to",
        " could be",
        " would be",
        " should consider",
    ]
    
    for pattern in conditional_patterns:
        if pattern in content or pattern in source:
            return False, f"Conditional statement: {fact.content[:50]}"
    
    # Rule 3: Must have commitment language for action items
    if fact.fact_type == "action_item":
        commitment_words = ["will", "going to", "please", "let's", "'ll", "send", "run", "schedule", "reach out", "set up", "ensure", "upload"]
        has_commitment = any(word in source for word in commitment_words)
        if not has_commitment:
            return False, f"No clear commitment: {fact.content[:50]}"
    
    # Rule 4: Must be specific enough
    vague_only_phrases = ["follow up", "look into", "think about", "work on", "check on"]
    for phrase in vague_only_phrases:
        # Only reject if the entire content is just the vague phrase
        if content.strip() == phrase or (phrase in content and len(content) < 20):
            return False, f"Too vague: {fact.content[:50]}"
    
    # Rule 5: Low confidence facts are discarded
    if fact.confidence == "low":
        return False, f"Low confidence: {fact.content[:50]}"
    
    return True, None
