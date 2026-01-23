#!/usr/bin/env python3
"""
Simple runner for meeting processor
Usage: python run.py [transcript_file.txt]
"""

import sys
import json
from pathlib import Path

# Import the main logic (modular V7)
from src.processor import process_meeting
from src.llm_provider import LLMProvider


def main():
    # Get transcript file
    transcript_file = sys.argv[1] if len(sys.argv) > 1 else "sample_transcript.txt"
    
    # Read transcript
    try:
        with open(transcript_file, 'r') as f:
            transcript = f.read()
        print(f"✓ Loaded: {transcript_file} ({len(transcript)} chars)\n")
    except FileNotFoundError:
        print(f"❌ File not found: {transcript_file}")
        print("\nUsage: python run.py [transcript_file.txt]")
        sys.exit(1)
    
    # Process
    try:
        outputs = process_meeting(
            transcription=transcript,
            provider=LLMProvider.OLLAMA,
            model_name="qwen2.5:latest",
            max_retries_per_output=2,
            consolidated_email=True  # Generate one email to all
        )
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Check if it worked
    if not outputs or not outputs.summary:
        print("\n❌ Processing failed. Check if Ollama is running:")
        print("   curl http://localhost:11434/api/tags")
        sys.exit(1)
    
    # Display results
    print("\n" + "="*70)
    print("📄 SUMMARY")
    print("="*70)
    print(outputs.summary)
    
    print(f"\n{'='*70}")
    print(f"📋 ACTION POINTS ({len(outputs.action_points)})")
    print("="*70)
    for i, ap in enumerate(outputs.action_points, 1):
        print(f"{i}. [{ap.priority}] {ap.description}")
        print(f"   Owner: {ap.stakeholder}")
    
    print(f"\n{'='*70}")
    print(f"✅ TO-DOS ({len(outputs.todos)})")
    print("="*70)
    for i, td in enumerate(outputs.todos, 1):
        print(f"{i}. [{td.priority}] {td.task}")
        print(f"   Assigned: {td.assigned_to} | Due: {td.deadline}")
    
    print(f"\n{'='*70}")
    print(f"📧 EMAILS ({len(outputs.follow_up_emails)})")
    print("="*70)
    for i, em in enumerate(outputs.follow_up_emails, 1):
        print(f"\n{i}. To: {em.recipient}")
        print(f"   Subject: {em.subject}")
        print(f"   Body: {em.body[:200]}...")
    
    # Save to JSON
    output_dir = Path("./results_v7")
    output_dir.mkdir(exist_ok=True)
    
    output_dict = {
        "summary": outputs.summary,
        "action_points": [
            {"description": ap.description, "priority": ap.priority, "stakeholder": ap.stakeholder}
            for ap in outputs.action_points
        ],
        "todos": [
            {"task": td.task, "assigned_to": td.assigned_to, "deadline": td.deadline, "priority": td.priority}
            for td in outputs.todos
        ],
        "follow_up_emails": [
            {"recipient": em.recipient, "subject": em.subject, "body": em.body}
            for em in outputs.follow_up_emails
        ]
    }
    
    json_file = output_dir / "meeting_outputs.json"
    with open(json_file, 'w') as f:
        json.dump(output_dict, f, indent=2)
    
    print(f"\n{'='*70}")
    print(f"✓ Saved to: {json_file}")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
