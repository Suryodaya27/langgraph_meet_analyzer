"""
Generate Todos (Single-Task Node)
"""

import json
from typing import Dict, Any
from src2.models import ToDo


def generate_todos(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Generate todos from validated facts with validation and retry"""
    
    validated = state["validated_facts"]
    
    # Filter relevant facts
    action_facts = [f for f in validated.facts if f.fact_type == "action_item"]
    deadline_facts = [f for f in validated.facts if f.fact_type == "deadline"]
    
    if not action_facts:
        print(f"✓ No action items for todos")
        return {**state, "todos": []}
    
    facts_text = "ACTION ITEMS:\n" + "\n".join([f"{i+1}. {f.content}" 
                                                for i, f in enumerate(action_facts)])
    
    if deadline_facts:
        facts_text += "\n\nDEADLINES:\n" + "\n".join([f"{i+1}. {f.content}" 
                                                       for i, f in enumerate(deadline_facts)])
    
    max_retries = 3
    feedback = ""
    
    for attempt in range(1, max_retries + 1):
        feedback_section = f"\n\nPREVIOUS ATTEMPT FEEDBACK:\n{feedback}\nFIX THESE ISSUES!" if feedback else ""
        
        prompt = f"""Create specific todos from these facts.{feedback_section}

CRITICAL RULES:
1. ONLY use these facts - no new information
2. Each todo should be ONE specific task (no duplicates)
3. SKIP ALL conditional items (anything with "if", "might", "may", "could")
4. Deadline format:
   - If there's a matching DEADLINE fact, copy it EXACTLY as stated
   - If no matching deadline, use null (JSON null, not the string "null" or "Not specified")
5. In source_facts, copy the EXACT text from facts above (word-for-word)
6. Aim for 3-5 todos maximum (quality over quantity)

FACTS:
{facts_text}

DEADLINE MATCHING EXAMPLES:

ACTION: "Send brief summary of API test"
DEADLINE: "Send summary by Friday morning"
→ deadline: "Friday morning" ✓

ACTION: "Run manual test on data mapping"
DEADLINE: None matching
→ deadline: null ✓ (NOT "Not specified" ✗)

WHAT TO SKIP:

✗ SKIP: "Push back launch if test fails" (conditional)
✗ SKIP: "Update docs if time permits" (conditional)

WHAT TO INCLUDE:

✓ INCLUDE: "Run manual test Thursday" (committed)
✓ INCLUDE: "Send Services copy by noon" (committed)

GOOD TODO EXAMPLES:

{{"task": "Run manual test on HubSpot API data mapping", "deadline": "Thursday", "priority": "High", "source_facts": ["Run manual test on data mapping Thursday"]}}

{{"task": "Send API test results summary", "deadline": "Friday morning", "priority": "High", "source_facts": ["Send brief summary by Friday morning"]}}

{{"task": "Obtain high-res assets from design team", "deadline": null, "priority": "Medium", "source_facts": ["Reach out to Chloe for assets"]}}

Return JSON array (3-5 items max):
[{{"task": "specific task here", "deadline": null, "priority": "High", "source_facts": ["exact fact text"]}}]

CRITICAL: Use JSON null for missing deadlines, NOT the string "Not specified" or "null"

Generate JSON array:"""

        try:
            response = llm.invoke(prompt)
            content = _clean_json(response.content)
            
            data = json.loads(content)
            todos = [ToDo(**td) for td in data]
            
            # Validate
            from src2.nodes.validate_outputs import _validate_todos_rules
            rule_score, rule_issues = _validate_todos_rules(todos)
            
            if rule_score < 8:
                if attempt < max_retries:
                    feedback = "RULE FAILURES:\n" + "\n".join([f"- {issue}" for issue in rule_issues])
                    print(f"  ⚠ Attempt {attempt}: Failed rules ({rule_score}/10), retrying...")
                    continue
                else:
                    print(f"  ⚠ Max retries reached, accepting current")
                    print(f"✓ Generated {len(todos)} todos")
                    return {**state, "todos": todos}
            
            print(f"✓ Generated {len(todos)} todos (validated: {rule_score}/10)")
            return {**state, "todos": todos}
            
        except Exception as e:
            if attempt < max_retries:
                feedback = f"ERROR: {str(e)}"
                print(f"  ⚠ Attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"✗ Todo generation failed after {max_retries} attempts: {e}")
                return {**state, "todos": []}


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
