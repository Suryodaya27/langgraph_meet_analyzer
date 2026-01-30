"""
Step 4d: Generate Email (Skills-Enhanced)
Uses GENERATE_EMAIL.md skill for professional follow-up emails
"""

import json
import re
from typing import Dict, Any
from src3.models import FollowUpEmail
from src3.skill_loader import load_skill


def generate_email(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Generate professional follow-up email using skill"""
    
    validated = state["validated_facts"]
    skill = load_skill("GENERATE_EMAIL")
    
    # Filter relevant facts
    relevant_facts = [f for f in validated.facts 
                     if f.fact_type in ["decision", "action_item", "deadline"]]
    
    if not relevant_facts:
        print(f"✓ No facts for email")
        return {**state, "follow_up_emails": []}
    
    facts_text = "\n".join([f"{i+1}. [{f.fact_type.upper()}] {f.content}" 
                           for i, f in enumerate(relevant_facts)])
    
    prompt = f"""# SKILL INSTRUCTIONS
{skill}

# VALIDATED FACTS
{facts_text}

# OUTPUT FORMAT
Return a JSON object with subject, body, and source_facts.
Keep the body simple - no special characters or line breaks.
No placeholders like [Your Name].

Example format:
{{"subject": "Meeting Follow-Up", "body": "Following up on our meeting. Key items: Item 1. Item 2. Best regards", "source_facts": ["fact 1", "fact 2"]}}

JSON:"""

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
            
            # Clean up email body
            if 'body' in data:
                body = data['body']
                body = re.sub(r'\n{3,}', '\n\n', body)
                body = re.sub(r'[ \t]+', ' ', body)
                # Add line breaks after bullet points for readability
                body = body.replace(' - ', '\n- ')
                body = body.replace('Best regards', '\n\nBest regards')
                data['body'] = body.strip()
            
            # Remove duplicate source_facts
            if 'source_facts' in data:
                data['source_facts'] = list(dict.fromkeys(data['source_facts']))
            
            email = FollowUpEmail(**data)
            
            # Validate
            issues = _validate_email(email)
            if issues and attempt < max_retries:
                feedback = "\n".join(issues)
                print(f"  ⚠ Attempt {attempt}: Validation issues, retrying...")
                continue
            
            print(f"✓ Generated follow-up email")
            return {**state, "follow_up_emails": [email]}
            
        except Exception as e:
            if attempt < max_retries:
                feedback = f"JSON parsing error: {str(e)}"
                print(f"  ⚠ Attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"  ⚠ Email JSON parsing failed, creating fallback email")
                # Create a simple fallback email from facts
                facts_list = [f.content for f in relevant_facts[:5]]
                fallback_body = "Following up on our meeting discussion:\n\n"
                fallback_body += "Key items:\n"
                for fact in facts_list:
                    fallback_body += f"- {fact}\n"
                fallback_body += "\nPlease let me know if you have any questions.\n\nBest regards"
                
                fallback_email = FollowUpEmail(
                    subject="Meeting Follow-Up - Action Items",
                    body=fallback_body,
                    source_facts=facts_list
                )
                print(f"✓ Generated fallback email")
                return {**state, "follow_up_emails": [fallback_email]}


def _validate_email(email: FollowUpEmail) -> list:
    """Validate email and return issues"""
    issues = []
    
    # Check for placeholders
    placeholders = ["[your name]", "[recipient]", "[date]", "[name]", "[company]"]
    body_lower = email.body.lower()
    for ph in placeholders:
        if ph in body_lower:
            issues.append(f"Contains placeholder: {ph} - remove all placeholders")
    
    # Check for conditionals
    if any(word in body_lower for word in [" if ", " might ", " may "]):
        issues.append("Contains conditional language - remove conditionals")
    
    # Check length
    word_count = len(email.body.split())
    if word_count < 50:
        issues.append(f"Too short ({word_count} words) - need at least 50 words")
    if word_count > 300:
        issues.append(f"Too long ({word_count} words) - keep under 200 words")
    
    return issues


def _clean_json(content: str) -> str:
    """Clean JSON from LLM response - aggressive cleaning for control characters"""
    content = content.strip()
    
    # Remove markdown code blocks
    if '```' in content:
        parts = content.split('```')
        if len(parts) >= 2:
            content = parts[1]
            if content.startswith('json'):
                content = content[4:]
            content = content.strip()
    
    # Extract JSON object
    if '{' in content:
        content = content[content.find('{'):]
    if '}' in content:
        content = content[:content.rfind('}') + 1]
    
    # Remove comments
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove ALL control characters (this is the key fix)
    content = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', content)
    
    # Fix common JSON issues
    content = re.sub(r',(\s*[}\]])', r'\1', content)  # Trailing commas
    content = re.sub(r'\s+', ' ', content)  # Normalize whitespace
    
    # Fix unescaped newlines in strings (common LLM error)
    # Replace literal newlines inside strings with \n
    def fix_string_newlines(match):
        s = match.group(0)
        # Replace actual newlines with escaped newlines
        s = s.replace('\n', '\\n').replace('\r', '\\r').replace('\t', '\\t')
        return s
    
    # This regex finds strings and fixes newlines inside them
    content = re.sub(r'"[^"]*"', fix_string_newlines, content)
    
    return content.strip()
