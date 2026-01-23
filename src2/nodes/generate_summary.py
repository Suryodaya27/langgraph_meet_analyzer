"""
Generate Summary (Single-Task Node with Validation + Feedback)
"""

from typing import Dict, Any
import json


def generate_summary(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Generate summary from validated facts with rule + AI validation"""
    
    validated = state["validated_facts"]
    transcript = state["raw_transcript"]
    
    # Format facts for LLM
    facts_text = _format_facts(validated.facts)
    
    max_retries = 3
    feedback = ""
    
    for attempt in range(1, max_retries + 1):
        feedback_section = f"\n\nPREVIOUS ATTEMPT FEEDBACK:\n{feedback}\nFIX THESE ISSUES!" if feedback else ""
        
        prompt = f"""Create a 2-3 sentence summary from these validated facts.{feedback_section}

CRITICAL RULES:
- ONLY use information from the facts below
- DO NOT add any new information, names, or numbers not in facts
- SKIP conditional statements (anything with "if", "might", "may")
- Focus on COMMITTED actions and CONFIRMED decisions only
- Be concise and professional
- Target: 50-100 words

VALIDATED FACTS:
{facts_text}

EXAMPLES:

BAD (includes conditionals):
"The dev site will be delayed if the API test fails..."

GOOD (only commitments):
"API testing will be completed Thursday with results summary due Friday morning. High-res assets to be obtained by Wednesday. UAT session scheduled for next Tuesday at 2:00 PM."

Generate ONLY the summary text (no labels):"""

        try:
            response = llm.invoke(prompt)
            summary = response.content.strip()
            
            # Remove common labels and prefixes
            labels_to_remove = [
                'Summary:', 'SUMMARY:', 'summary:',
                'Here is the summary:', 'Here is a summary:',
                'Here is a 50-100 word summary:',
                'Here is a 2-3 sentence summary:',
                'Based on the facts:', 'Based on committed actions:',
                'Here is a 50-100 word summary based on committed actions and confirmed decisions:',
            ]
            
            for label in labels_to_remove:
                if summary.startswith(label):
                    summary = summary[len(label):].strip()
            
            # Normalize whitespace - replace multiple newlines/spaces with single space
            import re
            summary = re.sub(r'\s+', ' ', summary).strip()
            
            # STEP 1: Rule validation (fast, free)
            rule_score, rule_issues = _validate_summary_rules(summary)
            
            if rule_score < 8:
                if attempt < max_retries:
                    feedback = f"RULE FAILURES:\n" + "\n".join([f"- {issue}" for issue in rule_issues])
                    print(f"  ⚠ Attempt {attempt}: Failed rules ({rule_score}/10), retrying...")
                    continue
                else:
                    print(f"  ⚠ Max retries reached, accepting current")
                    return {**state, "summary": summary}
            
            # STEP 2: AI validation (check for hallucinations)
            print(f"  ✓ Rules passed ({rule_score}/10), checking AI quality...")
            ai_result = _validate_summary_ai(summary, transcript, llm)
            
            if ai_result["score"] < 8:
                if attempt < max_retries:
                    feedback = f"AI QUALITY ISSUES:\n" + "\n".join([f"- {issue}" for issue in ai_result["issues"]])
                    if ai_result.get("suggestions"):
                        feedback += f"\n\nSUGGESTIONS:\n{ai_result['suggestions']}"
                    print(f"  ⚠ Attempt {attempt}: Failed AI check ({ai_result['score']}/10), retrying...")
                    continue
                else:
                    print(f"  ⚠ Max retries reached, accepting current")
                    return {**state, "summary": summary}
            
            # Both passed!
            final_score = (rule_score + ai_result["score"]) // 2
            print(f"  ✓ Attempt {attempt}: PASSED! Rules: {rule_score}/10, AI: {ai_result['score']}/10, Final: {final_score}/10")
            print(f"     ({len(summary.split())} words)")
            return {**state, "summary": summary}
            
        except Exception as e:
            if attempt < max_retries:
                feedback = f"ERROR: {str(e)}"
                print(f"  ⚠ Attempt {attempt} failed: {e}, retrying...")
            else:
                print(f"✗ Summary generation failed after {max_retries} attempts")
                # Fallback
                fact_summaries = [f.content for f in validated.facts[:5]]
                summary = "; ".join(fact_summaries) if fact_summaries else "No summary available"
                return {**state, "summary": summary}


def _validate_summary_rules(summary: str) -> tuple:
    """Rule-based validation"""
    score = 10
    issues = []
    
    word_count = len(summary.split())
    
    if word_count < 30:
        issues.append(f"Too short: {word_count} words (need 30+ minimum)")
        score -= 5
    elif word_count < 50:
        issues.append(f"Below target: {word_count} words (target 50+)")
        score -= 1
    
    return max(1, score), issues


def _validate_summary_ai(summary: str, transcript: str, llm) -> dict:
    """AI validation - check for hallucinations"""
    
    prompt = f"""Check if this summary has HALLUCINATIONS (invented information).

TRANSCRIPT:
{transcript[:2000]}...

SUMMARY:
{summary}

CRITICAL CHECKS:
- Are all names in the summary actually in the transcript?
- Are all facts/numbers actually mentioned?
- Are all decisions actually made (not just discussed)?

SCORING:
- 8-10: No hallucinations, accurate
- 6-7: Has hallucinations or major inaccuracies
- 1-5: Severe problems

Return ONLY valid JSON:
{{"score": 8, "issues": ["list specific hallucinations if any"], "suggestions": "how to fix"}}

If score < 8, list the hallucinations in "issues"."""

    try:
        response = llm.invoke(prompt)
        content = _clean_json_response(response.content)
        return json.loads(content)
    except:
        return {"score": 8, "issues": [], "suggestions": ""}


def _clean_json_response(content: str) -> str:
    """Clean JSON from LLM response"""
    content = content.strip()
    
    if "```" in content:
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    
    if "{" in content:
        content = content[content.find("{"):]
    if "}" in content:
        content = content[:content.rfind("}") + 1]
    
    return content.strip()


def _format_facts(facts: list) -> str:
    """Format facts for LLM"""
    if not facts:
        return "No facts available"
    
    formatted = []
    for i, fact in enumerate(facts, 1):
        formatted.append(f"{i}. [{fact.fact_type.upper()}] {fact.content}")
    
    return "\n".join(formatted)


