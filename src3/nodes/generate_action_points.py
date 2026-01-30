"""
Step 4b: Generate Action Points (Skills-Enhanced)
Uses GENERATE_ACTION_POINTS.md skill for strategic action points
"""

import json
import re
from typing import Dict, Any
from src3.models import ActionPoint
from src3.skill_loader import load_skill


def generate_action_points(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Generate strategic action points using professional skill"""
    
    validated = state["validated_facts"]
    skill = load_skill("GENERATE_ACTION_POINTS")
    
    # Filter relevant facts
    relevant_facts = [f for f in validated.facts 
                     if f.fact_type in ["decision", "action_item"]]
    
    if not relevant_facts:
        print(f"✓ No facts for action points")
        return {**state, "action_points": []}
    
    facts_text = "\n".join([f"{i+1}. {f.content}" 
                           for i, f in enumerate(relevant_facts)])
    
    prompt = f"""# SKILL INSTRUCTIONS
{skill}

# VALIDATED FACTS
{facts_text}

# OUTPUT FORMAT
Return ONLY a valid JSON array. Maximum 4 action points.
Group related facts into single action points.

[{{"description": "Strategic goal here", "priority": "High", "source_facts": ["exact fact text 1", "exact fact text 2"]}}]

JSON array:"""

    max_retries = 3
    feedback = ""
    
    for attempt in range(1, max_retries + 1):
        try:
            if feedback:
                prompt_with_feedback = prompt + f"\n\nPREVIOUS ATTEMPT FEEDBACK:\n{feedback}\nFIX THESE ISSUES!"
            else:
                prompt_with_feedback = prompt
            
            response = llm.invoke(prompt_with_feedback)
            content = _clean_json(response.content)
            
            data = json.loads(content)
            
            # Deduplicate source_facts
            for item in data:
                if 'source_facts' in item:
                    item['source_facts'] = list(dict.fromkeys(item['source_facts']))
            
            action_points = [ActionPoint(**ap) for ap in data]
            
            # Validate
            issues = _validate_action_points(action_points)
            if issues and attempt < max_retries:
                feedback = "\n".join(issues)
                print(f"  ⚠ Attempt {attempt}: Validation issues, retrying...")
                continue
            
            print(f"✓ Generated {len(action_points)} action points")
            return {**state, "action_points": action_points}
            
        except Exception as e:
            if attempt < max_retries:
                feedback = f"JSON parsing error: {str(e)}"
                print(f"  ⚠ Attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"✗ Action point generation failed")
                return {**state, "action_points": []}


def _validate_action_points(action_points: list) -> list:
    """Validate action points and return issues"""
    issues = []
    
    # Check for duplicates
    descriptions = [ap.description.lower().strip() for ap in action_points]
    if len(descriptions) != len(set(descriptions)):
        issues.append("Contains duplicate action points - group related items")
    
    # Check for conditionals
    for ap in action_points:
        if any(word in ap.description.lower() for word in [" if ", " might ", " may "]):
            issues.append(f"Contains conditional: '{ap.description}' - remove conditionals")
    
    # Check source_facts are actual text
    for ap in action_points:
        for sf in ap.source_facts:
            if sf.isdigit() or sf in ["1", "2", "3", "4", "5"]:
                issues.append(f"source_facts contains index '{sf}' - use actual fact text")
    
    return issues


def _clean_json(content: str) -> str:
    """Clean JSON from LLM response"""
    content = content.strip()
    
    if '```' in content:
        parts = content.split('```')
        if len(parts) >= 2:
            content = parts[1]
            if content.startswith('json'):
                content = content[4:]
    
    if '[' in content:
        content = content[content.find('['):]
    if ']' in content:
        content = content[:content.rfind(']') + 1]
    
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    
    return content.strip()
