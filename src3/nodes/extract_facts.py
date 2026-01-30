"""
Step 2: Extract Facts (Skills-Enhanced)
Uses EXTRACT_FACTS.md skill for professional-grade extraction
"""

import json
import re
from typing import Dict, Any, List
from src3.models import ExtractedFacts, ExtractedFact
from src3.skill_loader import load_skill


def extract_facts(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """
    Extract facts using skill-enhanced prompts.
    Each fact type is extracted separately for better accuracy.
    """
    
    transcript = state["normalized_transcript"]
    skill = load_skill("EXTRACT_FACTS")
    
    print("📊 Extracting facts with professional skill...")
    
    # Extract each fact type separately
    decisions = _extract_fact_type(transcript, "decision", skill, llm)
    action_items = _extract_fact_type(transcript, "action_item", skill, llm)
    deadlines = _extract_fact_type(transcript, "deadline", skill, llm)
    metrics = _extract_fact_type(transcript, "metric", skill, llm)
    
    # Combine into ExtractedFacts
    extracted = ExtractedFacts(
        decisions=decisions,
        action_items=action_items,
        open_questions=[],
        deadlines=deadlines,
        metrics=metrics
    )
    
    total = len(decisions) + len(action_items) + len(deadlines) + len(metrics)
    
    print(f"✓ Extracted {total} facts:")
    print(f"  - Decisions: {len(decisions)}")
    print(f"  - Action Items: {len(action_items)}")
    print(f"  - Deadlines: {len(deadlines)}")
    print(f"  - Metrics: {len(metrics)}")
    
    return {
        **state,
        "extracted_facts": extracted
    }


def _extract_fact_type(transcript: str, fact_type: str, skill: str, llm) -> List[ExtractedFact]:
    """Extract a specific fact type with skill guidance"""
    
    type_instructions = {
        "decision": "Extract DECISIONS - things that were decided/agreed upon. Must have finality words like 'decided', 'agreed', 'will', 'let's go with'.",
        "action_item": "Extract ACTION ITEMS - things someone committed to do. Must have 'I will', 'X will', 'please', or action verbs. SKIP conditionals.",
        "deadline": "Extract DEADLINES - explicit time references like 'Thursday', 'by noon', 'next Tuesday at 2pm', 'EOD Wednesday'.",
        "metric": "Extract METRICS - explicit numbers like '$3.5M', '3 hours', '12 clients', '23%'."
    }
    
    prompt = f"""# SKILL INSTRUCTIONS
{skill}

# SPECIFIC TASK
{type_instructions.get(fact_type, "")}

# TRANSCRIPT
{transcript}

# OUTPUT FORMAT
Return ONLY a valid JSON array. Each item must have:
- fact_type: "{fact_type}"
- content: Brief description
- source_quote: EXACT quote from transcript
- confidence: "high", "medium", or "low"

Example:
[{{"fact_type": "{fact_type}", "content": "description here", "source_quote": "exact words from transcript", "confidence": "high"}}]

If no {fact_type}s found, return empty array: []

JSON array:"""

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = llm.invoke(prompt)
            facts = _parse_fact_array(response.content, fact_type)
            return facts
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠ {fact_type} extraction attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"  ⚠ {fact_type} extraction failed after {max_retries} attempts")
                return []


def _parse_fact_array(content: str, fact_type: str) -> List[ExtractedFact]:
    """Parse JSON array from LLM response"""
    
    content = content.strip()
    
    # Remove markdown
    if '```' in content:
        parts = content.split('```')
        if len(parts) >= 2:
            content = parts[1]
            if content.startswith('json'):
                content = content[4:]
    
    # Extract array
    if '[' in content:
        content = content[content.find('['):]
    if ']' in content:
        content = content[:content.rfind(']') + 1]
    
    # Clean
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    
    content = content.strip()
    
    if not content or content == '[]':
        return []
    
    data = json.loads(content)
    
    facts = []
    for item in data:
        if isinstance(item, dict):
            try:
                facts.append(ExtractedFact(
                    fact_type=item.get('fact_type', fact_type),
                    content=item.get('content', ''),
                    source_quote=item.get('source_quote', ''),
                    confidence=item.get('confidence', 'high'),
                    context=item.get('context')
                ))
            except Exception:
                # Skip invalid items
                pass
    
    return facts
