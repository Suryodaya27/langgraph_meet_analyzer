"""
Validate Generated Outputs (Rule-Based + AI)
Two-layer validation: Rules first (fast), then AI (if rules pass)
"""

import json
from typing import Dict, Any, Tuple, List


def validate_summary_with_retry(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Validate summary with rule + AI checks, retry if needed"""
    
    summary = state.get("summary", "")
    transcript = state["raw_transcript"]
    
    # Rule-based validation (fast)
    rule_score, rule_issues = _validate_summary_rules(summary)
    
    if rule_score < 8:
        print(f"  ✗ Summary failed rules ({rule_score}/10): {', '.join(rule_issues)}")
        return {**state, "summary_validation_failed": True}
    
    # AI validation (check for hallucinations)
    ai_result = _validate_summary_ai(summary, transcript, llm)
    
    if ai_result["score"] < 8:
        print(f"  ✗ Summary failed AI check ({ai_result['score']}/10): {', '.join(ai_result['issues'])}")
        return {**state, "summary_validation_failed": True}
    
    print(f"  ✓ Summary validated (Rules: {rule_score}/10, AI: {ai_result['score']}/10)")
    return {**state, "summary_validation_failed": False}


def validate_action_points_with_retry(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Validate action points with rule + AI checks"""
    
    action_points = state.get("action_points", [])
    transcript = state["raw_transcript"]
    summary = state.get("summary", "")
    
    # Rule-based validation
    rule_score, rule_issues = _validate_actions_rules(action_points)
    
    if rule_score < 8:
        print(f"  ✗ Action points failed rules ({rule_score}/10): {', '.join(rule_issues)}")
        return {**state, "action_points_validation_failed": True}
    
    # AI validation (check for hallucinations)
    ai_result = _validate_actions_ai(action_points, transcript, summary, llm)
    
    if ai_result["score"] < 8:
        print(f"  ✗ Action points failed AI check ({ai_result['score']}/10): {', '.join(ai_result['issues'])}")
        return {**state, "action_points_validation_failed": True}
    
    print(f"  ✓ Action points validated (Rules: {rule_score}/10, AI: {ai_result['score']}/10)")
    return {**state, "action_points_validation_failed": False}


def validate_todos_with_retry(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Validate todos with rule + AI checks"""
    
    todos = state.get("todos", [])
    transcript = state["raw_transcript"]
    summary = state.get("summary", "")
    
    # Rule-based validation
    rule_score, rule_issues = _validate_todos_rules(todos)
    
    if rule_score < 8:
        print(f"  ✗ Todos failed rules ({rule_score}/10): {', '.join(rule_issues)}")
        return {**state, "todos_validation_failed": True}
    
    # AI validation (check for hallucinations)
    ai_result = _validate_todos_ai(todos, transcript, summary, llm)
    
    if ai_result["score"] < 8:
        print(f"  ✗ Todos failed AI check ({ai_result['score']}/10): {', '.join(ai_result['issues'])}")
        return {**state, "todos_validation_failed": True}
    
    print(f"  ✓ Todos validated (Rules: {rule_score}/10, AI: {ai_result['score']}/10)")
    return {**state, "todos_validation_failed": False}


def validate_email_with_retry(state: Dict[str, Any], llm) -> Dict[str, Any]:
    """Validate email with rule + AI checks"""
    
    emails = state.get("follow_up_emails", [])
    transcript = state["raw_transcript"]
    summary = state.get("summary", "")
    
    # Rule-based validation
    rule_score, rule_issues = _validate_emails_rules(emails)
    
    if rule_score < 8:
        print(f"  ✗ Email failed rules ({rule_score}/10): {', '.join(rule_issues)}")
        return {**state, "email_validation_failed": True}
    
    # AI validation (check for hallucinations)
    ai_result = _validate_emails_ai(emails, transcript, summary, llm)
    
    if ai_result["score"] < 8:
        print(f"  ✗ Email failed AI check ({ai_result['score']}/10): {', '.join(ai_result['issues'])}")
        return {**state, "email_validation_failed": True}
    
    print(f"  ✓ Email validated (Rules: {rule_score}/10, AI: {ai_result['score']}/10)")
    return {**state, "email_validation_failed": False}


# ============================================================================
# RULE-BASED VALIDATORS (Fast, Free)
# ============================================================================

def _validate_summary_rules(summary: str) -> Tuple[int, List[str]]:
    """Rule-based validation for summary"""
    score = 10
    issues = []
    
    word_count = len(summary.split())
    
    if word_count < 30:
        issues.append(f"Too short: {word_count} words (need 30+ minimum)")
        score -= 5
    elif word_count < 50:
        score -= 1
    
    return max(1, score), issues


def _validate_actions_rules(action_points: list) -> Tuple[int, List[str]]:
    """Rule-based validation for action points"""
    score = 10
    issues = []
    
    if len(action_points) < 1:
        issues.append("No action points generated")
        score -= 5
        return max(1, score), issues
    
    # Check for duplicates
    descriptions = [ap.description.lower().strip() for ap in action_points]
    unique_descriptions = set(descriptions)
    if len(descriptions) != len(unique_descriptions):
        issues.append("Contains duplicate action points")
        score -= 3
    
    # Check for overly detailed actions (should be strategic)
    for ap in action_points:
        if len(ap.description.split()) < 4:
            issues.append(f"Action too vague: '{ap.description}'")
            score -= 1
            break
    
    # Check for conditionals in descriptions or source_facts
    for i, ap in enumerate(action_points):
        desc = ap.description.lower()
        if any(word in desc for word in [" if ", " might ", " may ", " could "]):
            issues.append(f"Action {i+1} contains conditional language: '{ap.description}'")
            score -= 3
        
        # Check source_facts for conditionals
        if hasattr(ap, 'source_facts'):
            for fact in ap.source_facts:
                if any(word in fact.lower() for word in [" if ", " might ", " may ", " could "]):
                    issues.append(f"Action {i+1} source_facts contain conditional: '{fact}'")
                    score -= 2
                    break
    
    return max(1, score), issues


def _validate_todos_rules(todos: list) -> Tuple[int, List[str]]:
    """Rule-based validation for todos"""
    score = 10
    issues = []
    
    if len(todos) < 1:
        issues.append("No todos generated")
        score -= 5
        return max(1, score), issues
    
    # Check for wrong deadline format
    for i, todo in enumerate(todos):
        deadline = todo.deadline if hasattr(todo, 'deadline') else None
        
        # Deadline should be null or a date/time string, not a task description
        if deadline and deadline not in [None, "null"]:
            # Check if deadline looks like a task (has verbs like "run", "send", "schedule")
            task_verbs = ["run", "send", "schedule", "reach", "upload", "obtain", "complete", "review"]
            if any(verb in deadline.lower() for verb in task_verbs):
                issues.append(f"Todo {i+1} has task description as deadline: '{deadline}'")
                score -= 2
            
            # Check for "Not specified" or similar
            if deadline.lower() in ["not specified", "none", "n/a", "tbd", "not available"]:
                issues.append(f"Todo {i+1} has '{deadline}' instead of null")
                score -= 2
    
    # Check for duplicates
    tasks = [td.task.lower().strip() for td in todos]
    if len(tasks) != len(set(tasks)):
        issues.append("Contains duplicate todos")
        score -= 2
    
    # Check for conditionals in tasks
    for i, todo in enumerate(todos):
        task = todo.task.lower()
        if any(word in task for word in [" if ", " might ", " may ", " could "]):
            issues.append(f"Todo {i+1} contains conditional language: '{todo.task}'")
            score -= 2
    
    return max(1, score), issues


def _validate_emails_rules(emails: list) -> Tuple[int, List[str]]:
    """Rule-based validation for emails"""
    score = 10
    issues = []
    
    if len(emails) == 0:
        issues.append("No email generated")
        score -= 5
    else:
        for email in emails:
            body = email.body if hasattr(email, 'body') else ""
            if len(body.split()) < 50:
                issues.append(f"Email too short: {len(body.split())} words")
                score -= 3
    
    return max(1, score), issues


# ============================================================================
# AI-BASED VALIDATORS (Check for Hallucinations)
# ============================================================================

def _validate_summary_ai(summary: str, transcript: str, llm) -> dict:
    """AI validation for summary - check for hallucinations"""
    
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
{{"score": 8, "issues": [], "suggestions": ""}}

If score < 8, list the hallucinations in "issues"."""

    try:
        response = llm.invoke(prompt)
        content = _clean_json_response(response.content)
        return json.loads(content)
    except:
        return {"score": 8, "issues": [], "suggestions": ""}


def _validate_actions_ai(action_points: list, transcript: str, summary: str, llm) -> dict:
    """AI validation for action points - check for hallucinations"""
    
    actions_text = "\n".join([f"{i+1}. {ap.description}" for i, ap in enumerate(action_points)])
    
    prompt = f"""Check if these action points have HALLUCINATIONS.

TRANSCRIPT:
{transcript[:1500]}...

ACTION POINTS:
{actions_text}

CRITICAL CHECKS:
- Are all actions actually discussed/committed to?
- No invented stakeholders or goals?

SCORING:
- 8-10: No hallucinations
- 6-7: Has hallucinations
- 1-5: Severe problems

Return ONLY valid JSON:
{{"score": 8, "issues": [], "suggestions": ""}}"""

    try:
        response = llm.invoke(prompt)
        content = _clean_json_response(response.content)
        return json.loads(content)
    except:
        return {"score": 8, "issues": [], "suggestions": ""}


def _validate_todos_ai(todos: list, transcript: str, summary: str, llm) -> dict:
    """AI validation for todos - check for hallucinations"""
    
    todos_text = "\n".join([f"{i+1}. {td.task} (deadline: {td.deadline})" for i, td in enumerate(todos)])
    
    prompt = f"""Check if these todos have HALLUCINATIONS.

SUMMARY:
{summary}

TODOS:
{todos_text}

CRITICAL CHECKS:
- Are all tasks actually committed to?
- Are dates in 2026 (not wrong year)?
- No invented people or tasks?

SCORING:
- 8-10: No hallucinations
- 6-7: Has hallucinations
- 1-5: Severe problems

Return ONLY valid JSON:
{{"score": 8, "issues": [], "suggestions": ""}}"""

    try:
        response = llm.invoke(prompt)
        content = _clean_json_response(response.content)
        return json.loads(content)
    except:
        return {"score": 8, "issues": [], "suggestions": ""}


def _validate_emails_ai(emails: list, transcript: str, summary: str, llm) -> dict:
    """AI validation for emails - check for placeholders and quality"""
    
    email_text = emails[0].body if emails else ""
    
    prompt = f"""Check if this email is ready to send.

EMAIL:
{email_text}

CRITICAL CHECKS:
- No placeholders like [Your Name] or [Date]?
- Professional tone?
- Clear and actionable?

SCORING:
- 8-10: Ready to send
- 6-7: Has issues
- 1-5: Severe problems

Return ONLY valid JSON:
{{"score": 8, "issues": [], "suggestions": ""}}"""

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
