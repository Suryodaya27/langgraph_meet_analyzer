"""
Step 4c: Generate To-Dos (Skills-Enhanced)
Uses GENERATE_TODOS.md skill for actionable to-do items
"""

import json
import re
from typing import Dict, Any
from src3.models import ToDo
from src3.skill_loader import load_skill


def generate_todos(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Generate tactical to-dos using professional skill"""
    
    validated = state["validated_facts"]
    skill = load_skill("GENERATE_TODOS")
    
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
    
    prompt = f"""# SKILL INSTRUCTIONS
{skill}

# VALIDATED FACTS
{facts_text}

# OUTPUT FORMAT
Return ONLY a valid JSON array. Maximum 5 to-dos.
Match action items with deadlines where applicable.
Use JSON null for missing deadlines (NOT "Not specified").

[{{"task": "Specific task here", "deadline": null, "priority": "High", "source_facts": ["exact fact text"]}}]

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
            
            todos = [ToDo(**td) for td in data]
            
            # Validate and fix common issues
            todos = _fix_common_issues(todos)
            
            issues = _validate_todos(todos)
            if issues and attempt < max_retries:
                feedback = "\n".join(issues)
                print(f"  ⚠ Attempt {attempt}: Validation issues, retrying...")
                continue
            
            print(f"✓ Generated {len(todos)} todos")
            return {**state, "todos": todos}
            
        except Exception as e:
            if attempt < max_retries:
                feedback = f"JSON parsing error: {str(e)}"
                print(f"  ⚠ Attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"✗ Todo generation failed")
                return {**state, "todos": []}


def _fix_common_issues(todos: list) -> list:
    """Fix common LLM mistakes"""
    fixed = []
    for todo in todos:
        # Fix "Not specified" -> None
        if todo.deadline and todo.deadline.lower() in ["not specified", "none", "n/a", "tbd", "null"]:
            todo = ToDo(
                task=todo.task,
                deadline=None,
                priority=todo.priority,
                source_facts=todo.source_facts
            )
        
        # Fix deadline that looks like a task
        if todo.deadline:
            task_verbs = ["run", "send", "schedule", "reach", "upload", "complete", "review"]
            if any(verb in todo.deadline.lower() for verb in task_verbs):
                todo = ToDo(
                    task=todo.task,
                    deadline=None,
                    priority=todo.priority,
                    source_facts=todo.source_facts
                )
        
        fixed.append(todo)
    
    return fixed


def _validate_todos(todos: list) -> list:
    """Validate todos and return issues"""
    issues = []
    
    # Check for duplicates
    tasks = [td.task.lower().strip() for td in todos]
    if len(tasks) != len(set(tasks)):
        issues.append("Contains duplicate todos - remove duplicates")
    
    # Check for conditionals
    for td in todos:
        if any(word in td.task.lower() for word in [" if ", " might ", " may "]):
            issues.append(f"Contains conditional: '{td.task}' - remove conditionals")
    
    # Check source_facts are actual text
    for td in todos:
        for sf in td.source_facts:
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
