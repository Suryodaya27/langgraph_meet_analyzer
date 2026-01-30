"""
Step 4a: Generate Summary (Skills-Enhanced)
Uses GENERATE_SUMMARY.md skill for executive-quality summaries
"""

import re
from typing import Dict, Any
from src3.skill_loader import load_skill


def generate_summary(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Generate executive summary using professional skill"""
    
    validated = state["validated_facts"]
    skill = load_skill("GENERATE_SUMMARY")
    
    # Format facts
    facts_text = _format_facts(validated.facts)
    
    prompt = f"""# SKILL INSTRUCTIONS
{skill}

# VALIDATED FACTS TO SUMMARIZE
{facts_text}

# OUTPUT
Generate ONLY the summary text. No labels, no formatting, no "Here is...".
Target: 40-80 words, 2-4 sentences.

Summary:"""

    max_retries = 3
    feedback = ""
    
    for attempt in range(1, max_retries + 1):
        try:
            if feedback:
                prompt_with_feedback = prompt + f"\n\nPREVIOUS ATTEMPT FEEDBACK:\n{feedback}\nFIX THESE ISSUES!"
            else:
                prompt_with_feedback = prompt
            
            response = llm.invoke(prompt_with_feedback)
            summary = _clean_summary(response.content)
            
            # Validate
            word_count = len(summary.split())
            if word_count < 30:
                if attempt < max_retries:
                    feedback = f"Too short ({word_count} words). Need at least 40 words."
                    print(f"  ⚠ Attempt {attempt}: Too short, retrying...")
                    continue
            
            print(f"✓ Generated summary: {word_count} words")
            return {**state, "summary": summary}
            
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠ Attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"✗ Summary generation failed")
                # Fallback
                fact_summaries = [f.content for f in validated.facts[:5]]
                summary = ". ".join(fact_summaries) if fact_summaries else "No summary available."
                return {**state, "summary": summary}


def _clean_summary(text: str) -> str:
    """Clean summary output"""
    text = text.strip()
    
    # Remove common labels
    labels = [
        'Summary:', 'SUMMARY:', 'summary:',
        'Here is the summary:', 'Here is a summary:',
        'Here is a 40-80 word summary:',
        'Here is a 2-4 sentence summary:',
        'Based on the facts:', 'Based on the validated facts:',
    ]
    
    for label in labels:
        if text.lower().startswith(label.lower()):
            text = text[len(label):].strip()
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def _format_facts(facts: list) -> str:
    """Format facts for LLM"""
    if not facts:
        return "No facts available"
    
    formatted = []
    for i, fact in enumerate(facts, 1):
        formatted.append(f"{i}. [{fact.fact_type.upper()}] {fact.content}")
    
    return "\n".join(formatted)
