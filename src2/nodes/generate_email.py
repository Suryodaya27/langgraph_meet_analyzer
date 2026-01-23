"""
Generate Follow-Up Email (Single-Task Node)
"""

import json
from typing import Dict, Any
from src2.models import FollowUpEmail


def generate_email(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Generate follow-up email from validated facts ONLY with retry logic"""
    
    validated = state["validated_facts"]
    
    # Filter relevant facts
    relevant_facts = [f for f in validated.facts 
                     if f.fact_type in ["decision", "action_item", "deadline"]]
    
    if not relevant_facts:
        print(f"✓ No facts for email")
        return {**state, "follow_up_emails": []}
    
    facts_text = "\n".join([f"{i+1}. [{f.fact_type.upper()}] {f.content}" 
                           for i, f in enumerate(relevant_facts)])
    
    prompt = f"""Create a professional follow-up email from these facts.

CRITICAL RULES:
1. ONLY use these facts - no new information
2. Write in neutral/third-person tone (avoid "I will")
3. Be concise - focus on key commitments and deadlines
4. SKIP ALL conditional items (anything with "if", "might", "may", "could")
5. NO placeholders like [Your Name] or [Recipient]
6. End with "Best regards" or similar
7. In source_facts, copy the EXACT text from facts above (word-for-word)

FACTS:
{facts_text}

WHAT TO SKIP:
✗ "Push back launch if test fails" (conditional)
✗ "Might need to hire someone" (hypothetical)

WHAT TO INCLUDE:
✓ "API testing Thursday" (committed)
✓ "Summary due Friday morning" (committed)

EXAMPLE GOOD EMAIL:

Subject: Meeting Follow-Up - Action Items

Body:
Following up on our meeting discussion:

Key commitments:
- API testing to be completed Thursday with results summary due Friday morning
- High-res assets and mobile-optimized versions to be obtained by Wednesday EOD
- Services page copy to be sent for review by noon today
- UAT session scheduled for next Tuesday at 2:00 PM with sales team

Please let me know if you have any questions.

Best regards

---

Return JSON object:
{{"subject": "Meeting Follow-Up - Action Items", "body": "email text here", "source_facts": ["exact fact text 1", "exact fact text 2"]}}

Generate JSON object:"""

    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            response = llm.invoke(prompt)
            content = _clean_json(response.content)
            
            data = json.loads(content)
            
            # Clean up email body - normalize whitespace
            if 'body' in data:
                import re
                # Replace multiple newlines with double newline (paragraph break)
                body = data['body']
                body = re.sub(r'\n{3,}', '\n\n', body)  # Max 2 newlines
                body = re.sub(r'[ \t]+', ' ', body)  # Single spaces
                data['body'] = body.strip()
            
            email = FollowUpEmail(**data)
            
            print(f"✓ Generated follow-up email")
            
            return {
                **state,
                "follow_up_emails": [email]
            }
            
        except Exception as e:
            if attempt < max_retries:
                print(f"  ⚠ Email generation attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"✗ Email generation failed after {max_retries} attempts: {e}")
                return {**state, "follow_up_emails": []}


def _clean_json(content: str) -> str:
    """Clean JSON from LLM response"""
    import re
    
    content = content.strip()
    
    # Remove markdown
    if '```' in content:
        content = content.split('```')[1]
        if content.startswith('json'):
            content = content[4:]
    
    # Extract object
    if '{' in content:
        content = content[content.find('{'):]
    if '}' in content:
        content = content[:content.rfind('}') + 1]
    
    # Remove comments
    content = re.sub(r'//.*?$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Remove control chars
    content = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', content)
    
    # Fix trailing commas
    content = re.sub(r',(\s*[}\]])', r'\1', content)
    
    return content.strip()
