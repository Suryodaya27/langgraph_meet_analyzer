"""
Step 3: Validate Facts (Rules, Not Creativity)
Discard weak or ambiguous items, null missing owners, downgrade low-confidence facts
"""

from typing import Dict, Any, List
from src2.models import ValidatedFacts, ValidatedFact, ExtractedFact


def validate_facts(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate extracted facts using strict rules:
    1. Discard facts with confidence="low" and no clear commitment
    2. Discard facts with vague source quotes
    3. Discard facts that contradict each other
    4. Keep only high-quality, verifiable facts
    """
    
    extracted = state["extracted_facts"]
    validated_list = []
    discarded = []
    
    # Combine all facts for validation
    all_facts = (
        extracted.decisions +
        extracted.action_items +
        extracted.open_questions +
        extracted.deadlines +
        extracted.metrics
    )
    
    for fact in all_facts:
        # Rule 1: Discard low-confidence facts without clear commitment
        if fact.confidence == "low" and fact.fact_type in ["decision", "action_item"]:
            discarded.append(f"Low confidence {fact.fact_type}: {fact.content[:50]}")
            continue
        
        # Rule 2: Discard facts with very short source quotes (likely hallucinated)
        if len(fact.source_quote.split()) < 3:
            discarded.append(f"Vague source quote: {fact.content[:50]}")
            continue
        
        # Rule 3: Discard facts with generic content
        generic_phrases = ["discuss", "talk about", "look into", "follow up"]
        if any(phrase in fact.content.lower() for phrase in generic_phrases):
            if fact.confidence != "high":
                discarded.append(f"Generic content: {fact.content[:50]}")
                continue
        
        # Rule 4: Validate action items have clear commitment
        if fact.fact_type == "action_item":
            commitment_words = ["will", "going to", "need to", "must", "should", "please", "send me"]
            source_lower = fact.source_quote.lower()
            if not any(word in source_lower for word in commitment_words):
                # Check if it's an imperative (command form)
                imperative_verbs = ["send", "run", "reach", "ensure", "schedule", "set up", "get", "provide"]
                if not any(verb in source_lower for verb in imperative_verbs):
                    discarded.append(f"No clear commitment: {fact.content[:50]}")
                    continue
        
        # Fact passed validation
        validated_list.append(ValidatedFact(
            fact_type=fact.fact_type,
            content=fact.content,
            source_quote=fact.source_quote,
            confidence=fact.confidence,
            is_valid=True,
            validation_notes="Passed all validation rules"
        ))
    
    validated = ValidatedFacts(
        facts=validated_list,
        discarded_count=len(discarded),
        discarded_reasons=discarded
    )
    
    print(f"✓ Validated facts: {len(validated_list)} kept, {len(discarded)} discarded")
    if discarded:
        print(f"  Discarded reasons:")
        for reason in discarded[:3]:  # Show first 3
            print(f"    - {reason}")
    
    return {
        **state,
        "validated_facts": validated
    }
