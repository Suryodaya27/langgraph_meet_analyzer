"""
Generate Action Points (Single-Task Node)
"""

import json
from typing import Dict, Any
from src2.models import ActionPoint


def generate_action_points(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Generate action points from validated facts with validation and retry"""
    
    validated = state["validated_facts"]
    
    # Filter relevant facts
    relevant_facts = [f for f in validated.facts 
                     if f.fact_type in ["decision", "action_item"]]
    
    if not relevant_facts:
        print(f"✓ No facts for action points")
        return {**state, "action_points": []}
    
    facts_text = "\n".join([f"{i+1}. {f.content}" 
                           for i, f in enumerate(relevant_facts)])
    
    max_retries = 3
    feedback = ""
    
    for attempt in range(1, max_retries + 1):
        feedback_section = f"\n\nPREVIOUS ATTEMPT FEEDBACK:\n{feedback}\nFIX THESE ISSUES!" if feedback else ""
        
        prompt = f"""Create strategic action points from these facts.{feedback_section}

CRITICAL RULES:
1. ONLY use these facts - no new information
2. Group related facts into ONE action point (avoid duplicates)
3. Focus on HIGH-LEVEL strategic goals, not micro-tasks
4. SKIP ALL conditional/hypothetical items:
   - Anything with "if", "might", "may", "could", "would"
   - Contingency plans that weren't decided
   - Risks or problems mentioned but not committed to fix
5. In source_facts, copy the EXACT text from facts above (word-for-word)
6. Aim for 2-4 action points maximum (quality over quantity)

FACTS:
{facts_text}

EXAMPLES OF WHAT TO SKIP:

✗ SKIP: "Push back launch if test fails" (conditional - not a decision)
✗ SKIP: "Update docs if needed" (conditional)
✗ SKIP: "We might need to hire someone" (hypothetical)

EXAMPLES OF WHAT TO INCLUDE:

✓ INCLUDE: "Run API test on Thursday" (committed action)
✓ INCLUDE: "Send summary by Friday morning" (committed action)

GOOD ACTION POINT (strategic, grouped):
- Description: "Complete API testing and provide results summary"
  Source_facts: ["Run manual test on data mapping Thursday", "Send brief summary by Friday morning"]
  Priority: "High"

Return JSON array (2-4 items max):
[{{"description": "strategic goal here", "priority": "High", "source_facts": ["exact fact text 1", "exact fact text 2"]}}]

Generate JSON array:"""

        try:
            response = llm.invoke(prompt)
            content = _clean_json(response.content)
            
            data = json.loads(content)
            action_points = [ActionPoint(**ap) for ap in data]
            
            # Validate
            from src2.nodes.validate_outputs import _validate_actions_rules
            rule_score, rule_issues = _validate_actions_rules(action_points)
            
            if rule_score < 8:
                if attempt < max_retries:
                    feedback = "RULE FAILURES:\n" + "\n".join([f"- {issue}" for issue in rule_issues])
                    print(f"  ⚠ Attempt {attempt}: Failed rules ({rule_score}/10), retrying...")
                    continue
                else:
                    print(f"  ⚠ Max retries reached, accepting current")
                    print(f"✓ Generated {len(action_points)} action points")
                    return {**state, "action_points": action_points}
            
            print(f"✓ Generated {len(action_points)} action points (validated: {rule_score}/10)")
            return {**state, "action_points": action_points}
            
        except Exception as e:
            if attempt < max_retries:
                feedback = f"ERROR: {str(e)}"
                print(f"  ⚠ Attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"✗ Action point generation failed after {max_retries} attempts: {e}")
                return {**state, "action_points": []}


def _clean_json(content: str) -> str:
    """Clean JSON from LLM response"""
    import re
    
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
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove control chars
    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
    
    # Fix trailing commas
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    
    return content.strip()
