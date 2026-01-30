"""
Run Meeting Processor V9 - Skills-Enhanced Architecture
"""

from dotenv import load_dotenv
load_dotenv()

from src3.processor import process_meeting, save_outputs, print_outputs
from src3.llm_provider import LLMProvider


def main():
    # Read transcript
    with open("transcript2.txt", "r") as f:
        transcript = f.read()
    
    print("Processing meeting with V9 (Skills-Enhanced Architecture)...")
    
    # Process with your preferred provider
    # Options: LLMProvider.OPENAI, LLMProvider.GEMINI, LLMProvider.OLLAMA
    result = process_meeting(
        transcription=transcript,
        provider=LLMProvider.OLLAMA,
        model_name="qwen2.5:latest"  # or "gpt-4o" for OpenAI
    )
    
    # Save outputs
    output_file = save_outputs(result)
    print(f"\n✓ Saved outputs to: {output_file}")
    
    # Print outputs
    print_outputs(result)


if __name__ == "__main__":
    main()
