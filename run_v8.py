"""
Runner for V8 Fact-First Processor
"""

from src2.llm_provider import LLMProvider
from src2.processor import process_meeting, save_outputs


def main():
    # Read transcript
    with open("transcript2.txt", "r") as f:
        transcript = f.read()
    
    print("Processing meeting with V8 (Fact-First Architecture)...")
    
    # Process
    result = process_meeting(
        transcript,
        provider=LLMProvider.OLLAMA,
        # model_name="qwen2.5:latest"
        model_name = "llama3.1:8b"
    )
    
    # Save
    save_outputs(result, "results_v8/meeting_outputs.json")
    
    # Display summary
    outputs = result["outputs"]
    print("\n" + "="*70)
    print("OUTPUTS")
    print("="*70)
    print(f"\n📄 SUMMARY")
    print("-"*70)
    print(outputs.summary)
    
    print(f"\n📋 ACTION POINTS ({len(outputs.action_points)})")
    print("-"*70)
    for i, ap in enumerate(outputs.action_points, 1):
        print(f"{i}. [{ap.priority}] {ap.description}")
        if ap.source_facts:
            print(f"   Sources: {len(ap.source_facts)} facts")
    
    print(f"\n✅ TO-DOS ({len(outputs.todos)})")
    print("-"*70)
    for i, td in enumerate(outputs.todos, 1):
        print(f"{i}. [{td.priority}] {td.task}")
        print(f"   Deadline: {td.deadline}")
        if td.source_facts:
            print(f"   Sources: {len(td.source_facts)} facts")
    
    print(f"\n📧 EMAILS ({len(outputs.follow_up_emails)})")
    print("-"*70)
    for i, em in enumerate(outputs.follow_up_emails, 1):
        print(f"{i}. {em.subject}")
        print(f"   Body: {len(em.body)} chars")
        if em.source_facts:
            print(f"   Sources: {len(em.source_facts)} facts")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
