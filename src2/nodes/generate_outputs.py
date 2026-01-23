"""
Step 4: Generate Derived Outputs
Create summary, todos, and emails using ONLY validated facts
"""

import json
from typing import Dict, Any
from datetime import datetime
from src2.models import MeetingOutputs, ActionPoint, ToDo, FollowUpEmail


def generate_outputs(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """
    Generate all outputs from validated facts ONLY.
    No access to original transcript - prevents re-interpretation.
    """
    
    validated = state["validated_facts"]
    
    # Prepare facts for LLM
    facts_text = _format_facts_for_generation(validated.facts)
    
    current_date = datetime.now().strftime("%B %d, %Y")
    current_year = datetime.now().year
    
    prompt = f"""You are generating meeting outputs from VALIDATED FACTS ONLY.

CRITICAL RULES:
1. ONLY use information from the facts below
2. DO NOT add any new information
3. DO NOT invent names, dates, or commitments
4. If a fact doesn't have enough detail, skip it
5. Current date: {current_date}

VALIDATED FACTS:
{facts_text}

YOUR TASK:
Generate meeting outputs using ONLY the facts above.

OUTPUT FORMAT (JSON):
{{
  "summary": "2-3 sentence summary of key facts",
  "action_points": [
    {{
      "description": "Strategic action from facts",
      "priority": "High|Medium|Low",
      "source_facts": ["fact content 1", "fact content 2"]
    }}
  ],
  "todos": [
    {{
      "task": "Specific task from facts",
      "deadline": "2026-MM-DD or null if not specified",
      "priority": "High|Medium|Low",
      "source_facts": ["fact content"]
    }}
  ],
  "follow_up_emails": [
    {{
      "subject": "Meeting Follow-Up",
      "body": "Email body using facts only (no placeholders like [Your Name])",
      "source_facts": ["fact content 1", "fact content 2"]
    }}
  ]
}}

GUIDELINES:
- Summary: Synthesize key decisions and action items from facts
- Action Points: High-level goals from decision and action_item facts
- Todos: Specific tasks from action_item facts
  * ONLY include deadline if there's a DEADLINE fact with a specific date
  * If deadline is vague ("this week", "soon"), set to null
  * DO NOT calculate or invent dates
- Email: One general follow-up summarizing facts
  * NO placeholders like "[Your Name]" - just end with "Best regards" or similar

CRITICAL: 
- If you don't have enough facts for a section, return empty array
- Better to have less data than invented data
- ONLY include deadlines that are explicitly stated in facts
- DO NOT calculate dates from relative terms

Generate the JSON:"""

    try:
        response = llm.invoke(prompt)
        content = response.content.strip()
        
        # Aggressive JSON extraction
        # Remove everything before first {
        if '{' in content:
            content = content[content.find('{'):]
        
        # Remove everything after last }
        if '}' in content:
            content = content[:content.rfind('}') + 1]
        
        # Remove markdown code blocks
        content = content.replace('```json', '').replace('```', '')
        
        # Remove JSON comments (// and /* */)
        import re
        content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)  # Remove // comments
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)  # Remove /* */ comments
        
        # Remove control characters
        content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
        
        # Fix trailing commas
        content = re.sub(r',(\s*[}\]])', r'\1', content)
        
        # Fix unescaped quotes in strings (common LLM error)
        # This is a simple fix - may need refinement
        
        content = content.strip()
        
        print(f"  [DEBUG] Attempting to parse {len(content)} chars of JSON")
        
        data = json.loads(content)
        
        # Parse outputs
        outputs = MeetingOutputs(
            summary=data.get("summary", "No summary generated"),
            action_points=[ActionPoint(**ap) for ap in data.get("action_points", [])],
            todos=[ToDo(**td) for td in data.get("todos", [])],
            follow_up_emails=[FollowUpEmail(**em) for em in data.get("follow_up_emails", [])],
            total_facts_extracted=len(state["extracted_facts"].decisions) + 
                                 len(state["extracted_facts"].action_items) +
                                 len(state["extracted_facts"].open_questions) +
                                 len(state["extracted_facts"].deadlines) +
                                 len(state["extracted_facts"].metrics),
            total_facts_validated=len(validated.facts),
            facts_discarded=validated.discarded_count
        )
        
        print(f"✓ Generated outputs:")
        print(f"  - Summary: {len(outputs.summary)} chars")
        print(f"  - Action Points: {len(outputs.action_points)}")
        print(f"  - Todos: {len(outputs.todos)}")
        print(f"  - Emails: {len(outputs.follow_up_emails)}")
        
        return {
            **state,
            "outputs": outputs
        }
        
    except json.JSONDecodeError as e:
        print(f"✗ JSON parsing failed: {e}")
        print(f"  [DEBUG] Problematic JSON around char {e.pos}: ...{content[max(0,e.pos-50):e.pos+50]}...")
        
        # Try to salvage by creating minimal outputs from facts
        print(f"  [FALLBACK] Creating minimal outputs from validated facts")
        
        # Create simple summary from facts
        fact_summaries = [f.content for f in validated.facts[:5]]  # First 5 facts
        summary = "Key points: " + "; ".join(fact_summaries) if fact_summaries else "No summary available"
        
        outputs = MeetingOutputs(
            summary=summary,
            action_points=[],
            todos=[],
            follow_up_emails=[],
            total_facts_extracted=len(state["extracted_facts"].decisions) + 
                                 len(state["extracted_facts"].action_items) +
                                 len(state["extracted_facts"].open_questions) +
                                 len(state["extracted_facts"].deadlines) +
                                 len(state["extracted_facts"].metrics),
            total_facts_validated=len(validated.facts),
            facts_discarded=validated.discarded_count
        )
        
        return {
            **state,
            "outputs": outputs
        }
        
    except Exception as e:
        print(f"✗ Output generation failed: {e}")
        return {
            **state,
            "outputs": MeetingOutputs(
                summary="Error generating outputs",
                total_facts_extracted=0,
                total_facts_validated=len(validated.facts),
                facts_discarded=validated.discarded_count
            )
        }


def _format_facts_for_generation(facts: list) -> str:
    """Format validated facts for LLM consumption"""
    
    if not facts:
        return "No validated facts available."
    
    formatted = []
    for i, fact in enumerate(facts, 1):
        formatted.append(
            f"{i}. [{fact.fact_type.upper()}] {fact.content}\n"
            f"   Source: \"{fact.source_quote}\"\n"
            f"   Confidence: {fact.confidence}"
        )
    
    return "\n\n".join(formatted)
