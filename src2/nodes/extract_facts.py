"""
Step 2: Extract Facts (Multiple Single-Task LLM Calls)
Each call extracts ONE fact type with simple JSON
"""

import json
from typing import Dict, Any
from src2.models import ExtractedFacts, ExtractedFact


def extract_facts(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """
    Extract facts in separate focused calls.
    Each call extracts ONE fact type with simple JSON array.
    """
    
    transcript = state["normalized_transcript"]
    
    # Extract each fact type separately
    decisions = _extract_decisions(transcript, llm)
    action_items = _extract_action_items(transcript, llm)
    deadlines = _extract_deadlines(transcript, llm)
    metrics = _extract_metrics(transcript, llm)
    
    # Combine into ExtractedFacts
    extracted = ExtractedFacts(
        decisions=decisions,
        action_items=action_items,
        open_questions=[],  # Skip for now - rarely useful
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


def _extract_decisions(transcript: str, llm) -> list:
    """Extract ONLY decisions with retry logic"""
    
    prompt = f"""Extract decisions from this transcript.

RULES:
- ONLY extract if a clear decision was made
- Must have commitment words: "decided", "will", "let's", "going to"
- Include exact source quote
- Return valid JSON array

TRANSCRIPT:
{transcript}

Return ONLY this JSON array format (no extra text):
[{{"fact_type": "decision", "content": "brief description", "source_quote": "exact quote", "confidence": "high"}}]

JSON array:"""

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = llm.invoke(prompt)
            return _parse_fact_array(response.content, "decision")
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠ Decision extraction attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"  ⚠ Decision extraction failed after {max_retries} attempts: {e}")
                return []


def _extract_action_items(transcript: str, llm) -> list:
    """Extract ONLY action items with retry logic"""
    
    prompt = f"""Extract action items from this transcript.

RULES:
- ONLY extract if someone COMMITS to do something (not just discusses it)
- Must have commitment words: "I will", "X will", "please", or imperative verb
- SKIP conditional statements with "if", "might", "may", "could"
- Include exact source quote

EXAMPLES:
✓ EXTRACT: "I will run a test on Thursday" (commitment)
✓ EXTRACT: "Please send me the summary by Friday" (request = commitment)
✗ SKIP: "If it fails, we might push back the launch" (conditional, not committed)
✗ SKIP: "We should probably update the docs" (suggestion, not commitment)

TRANSCRIPT:
{transcript}

Return JSON array:
[{{"fact_type": "action_item", "content": "brief description", "source_quote": "exact quote", "confidence": "high"}}]

Generate JSON array:"""

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = llm.invoke(prompt)
            return _parse_fact_array(response.content, "action_item")
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠ Action item extraction attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"  ⚠ Action item extraction failed after {max_retries} attempts: {e}")
                return []


def _extract_deadlines(transcript: str, llm) -> list:
    """Extract ONLY deadlines with retry logic"""
    
    prompt = f"""Extract deadlines from this transcript.

RULES:
- ONLY extract explicit time references
- Examples: "Thursday", "Friday morning", "next Tuesday at 2pm", "by noon today"
- Include exact source quote

TRANSCRIPT:
{transcript}

Return JSON array:
[{{"fact_type": "deadline", "content": "brief description", "source_quote": "exact quote", "confidence": "high"}}]

Generate JSON array:"""

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = llm.invoke(prompt)
            return _parse_fact_array(response.content, "deadline")
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠ Deadline extraction attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"  ⚠ Deadline extraction failed after {max_retries} attempts: {e}")
                return []


def _extract_metrics(transcript: str, llm) -> list:
    """Extract ONLY metrics/numbers with retry logic"""
    
    prompt = f"""Extract numbers and metrics from this transcript.

RULES:
- ONLY extract explicit numbers mentioned
- Examples: "$3.5M", "3 hours", "23%", "10 clients"
- Include exact source quote
- fact_type MUST be "metric" (not "timeframe" or anything else)
- Return valid JSON array

TRANSCRIPT:
{transcript}

Return ONLY this JSON array format (no extra text):
[{{"fact_type": "metric", "content": "brief description", "source_quote": "exact quote", "confidence": "high"}}]

JSON array:"""

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = llm.invoke(prompt)
            return _parse_fact_array(response.content, "metric")
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠ Metric extraction attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"  ⚠ Metric extraction failed after {max_retries} attempts: {e}")
                return []


def _parse_fact_array(content: str, fact_type: str) -> list:
    """Parse simple JSON array from LLM response"""
    
    # Clean JSON
    content = content.strip()
    
    # Remove markdown
    if '```' in content:
        content = content.split('```')[1]
        if content.startswith('json'):
            content = content[4:]
    
    # Extract array
    if '[' in content:
        content = content[content.find('['):]
    if ']' in content:
        content = content[:content.rfind(']') + 1]
    
    # Remove comments
    import re
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove control chars
    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
    
    # Fix trailing commas
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    
    content = content.strip()
    
    # Parse
    data = json.loads(content)
    
    # Convert to ExtractedFact objects
    facts = []
    for item in data:
        if isinstance(item, dict):
            facts.append(ExtractedFact(
                fact_type=item.get('fact_type', fact_type),
                content=item.get('content', ''),
                source_quote=item.get('source_quote', ''),
                confidence=item.get('confidence', 'high'),
                context=item.get('context')
            ))
    
    return facts
