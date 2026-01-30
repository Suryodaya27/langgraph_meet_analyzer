"""
Main processor interface for V9 Skills-Enhanced Architecture
"""

import json
from pathlib import Path
from datetime import datetime

from src3.llm_provider import LLMProvider, get_llm
from src3.graph import process_meeting_v9
from src3.models import MeetingOutputs


def process_meeting(
    transcription: str,
    provider: LLMProvider = LLMProvider.OLLAMA,
    model_name: str = None
) -> dict:
    """
    Process meeting transcript with skills-enhanced architecture.
    
    Args:
        transcription: Meeting transcript text
        provider: LLM provider (OPENAI, GEMINI, OLLAMA)
        model_name: Model name (e.g., "gpt-4o", "qwen2.5:latest")
    
    Returns:
        Final state with outputs
    """
    
    llm = get_llm(provider, model_name)
    return process_meeting_v9(transcription, llm)


def save_outputs(result: dict, output_dir: str = "results_v9") -> str:
    """Save outputs to JSON file"""
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    outputs = result["outputs"]
    
    # Convert to dict for JSON serialization
    output_data = {
        "summary": outputs.summary,
        "action_points": [
            {
                "description": ap.description,
                "priority": ap.priority,
                "source_facts": ap.source_facts
            }
            for ap in outputs.action_points
        ],
        "todos": [
            {
                "task": td.task,
                "deadline": td.deadline,
                "priority": td.priority,
                "source_facts": td.source_facts
            }
            for td in outputs.todos
        ],
        "follow_up_emails": [
            {
                "subject": em.subject,
                "body": em.body,
                "source_facts": em.source_facts
            }
            for em in outputs.follow_up_emails
        ],
        "metadata": {
            "total_facts_extracted": outputs.total_facts_extracted,
            "total_facts_validated": outputs.total_facts_validated,
            "facts_discarded": outputs.facts_discarded,
            "compliance_passed": result.get("compliance_passed", False),
            "compliance_issues": result.get("compliance_issues", []),
            "processing_started": result.get("processing_started"),
            "processing_completed": result.get("processing_completed")
        }
    }
    
    output_file = output_path / "meeting_outputs.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    return str(output_file)


def print_outputs(result: dict):
    """Print outputs in a readable format"""
    
    outputs = result["outputs"]
    
    print("\n" + "="*70)
    print("OUTPUTS")
    print("="*70)
    
    print("\n📄 SUMMARY")
    print("-"*70)
    print(outputs.summary)
    
    print(f"\n📋 ACTION POINTS ({len(outputs.action_points)})")
    print("-"*70)
    for i, ap in enumerate(outputs.action_points, 1):
        print(f"{i}. [{ap.priority}] {ap.description}")
        print(f"   Sources: {len(ap.source_facts)} facts")
    
    print(f"\n✅ TO-DOS ({len(outputs.todos)})")
    print("-"*70)
    for i, td in enumerate(outputs.todos, 1):
        print(f"{i}. [{td.priority}] {td.task}")
        print(f"   Deadline: {td.deadline or 'None'}")
        print(f"   Sources: {len(td.source_facts)} facts")
    
    print(f"\n📧 EMAILS ({len(outputs.follow_up_emails)})")
    print("-"*70)
    for i, em in enumerate(outputs.follow_up_emails, 1):
        print(f"{i}. {em.subject}")
        print(f"   Body: {len(em.body)} chars")
        print(f"   Sources: {len(em.source_facts)} facts")
    
    print("\n" + "="*70)
