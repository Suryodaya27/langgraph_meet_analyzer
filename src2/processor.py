"""
Main processor interface for V8 (fully independent)
"""

import sys
sys.path.append('..')

from src2.llm_provider import LLMProvider, get_llm
from src2.graph import process_meeting_v8
from src2.models import MeetingOutputs
import json


def process_meeting(
    transcription: str,
    provider: LLMProvider = LLMProvider.OLLAMA,
    model_name: str = None
) -> dict:
    """
    Process meeting using fact-first architecture (V8).
    
    Args:
        transcription: Meeting transcript text
        provider: LLM provider (OPENAI, GEMINI, OLLAMA)
        model_name: Model name (e.g., "gpt-4o", "qwen2.5:latest")
    
    Returns:
        Dictionary with outputs and metadata
    """
    
    # Get LLM (reuse from src)
    llm = get_llm(provider, model_name)
    
    # Process using fact-first workflow
    result = process_meeting_v8(transcription, llm)
    
    return result


def save_outputs(result: dict, output_path: str = "results_v8/meeting_outputs.json"):
    """Save outputs to JSON file"""
    
    import os
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Extract outputs
    outputs = result["outputs"]
    
    # Convert to dict for JSON serialization
    output_dict = {
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
                "deadline": td.deadline if td.deadline else "Not specified",
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
            "compliance_passed": result["compliance_passed"],
            "compliance_issues": result["compliance_issues"],
            "processing_started": result.get("processing_started"),
            "processing_completed": result.get("processing_completed")
        }
    }
    
    with open(output_path, 'w') as f:
        json.dump(output_dict, f, indent=2)
    
    print(f"✓ Saved outputs to: {output_path}")
    
    return output_path


if __name__ == "__main__":
    # Test with sample transcript
    test_transcript = """
    Date: January 19, 2026
    Participants: Sarah Jenkins (Project Manager), Mark Thompson (Lead Developer)
    
    Sarah: Morning, Mark. I want to finalize the roadmap for the website relaunch.
    
    Mark: Sounds good. I have concerns about the API integration. The HubSpot API 
    documentation is outdated. I will run a manual test this Thursday. It will take 
    about three hours. If it fails, we might have to push the launch back by a week.
    
    Sarah: Understood. Mark, please send me a summary of that API test by Friday morning.
    
    Mark: Will do. The hero images are still missing.
    
    Sarah: I will reach out to Chloe today to get all high-res assets uploaded by 
    Wednesday. I'll also send you the Services page copy by noon today.
    
    Mark: Perfect. We need to schedule UAT for next week.
    
    Sarah: Good catch. I'll set up a UAT session for next Tuesday at 2:00 PM with 
    the sales team.
    """
    
    result = process_meeting(test_transcript, LLMProvider.OLLAMA, "qwen2.5:latest")
    save_outputs(result)
