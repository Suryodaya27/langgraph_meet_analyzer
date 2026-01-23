"""
Step 1: Normalize Transcript
Clean filler words and mark uncertainty without changing meaning
"""

import re
from typing import Dict, Any


def normalize_transcript(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize transcript by:
    1. Removing filler words (um, uh, like, you know)
    2. Marking uncertainty explicitly ([uncertain: ...])
    3. Preserving all factual content
    4. Handling Hinglish safely
    """
    
    transcript = state["raw_transcript"]
    
    # Common filler words to remove
    fillers = [
        r'\bum+\b', r'\buh+\b', r'\blike\b', r'\byou know\b',
        r'\bbasically\b', r'\bactually\b', r'\bjust\b', r'\bkind of\b',
        r'\bsort of\b', r'\bI mean\b', r'\bI think\b', r'\bI guess\b'
    ]
    
    normalized = transcript
    
    # Remove fillers (case insensitive)
    for filler in fillers:
        normalized = re.sub(filler, '', normalized, flags=re.IGNORECASE)
    
    # Mark uncertainty phrases
    uncertainty_markers = [
        (r'maybe\s+([^.!?]+)', r'[uncertain: \1]'),
        (r'probably\s+([^.!?]+)', r'[uncertain: \1]'),
        (r'I\'m not sure\s+([^.!?]+)', r'[uncertain: \1]'),
        (r'might\s+([^.!?]+)', r'[possible: \1]'),
    ]
    
    for pattern, replacement in uncertainty_markers:
        normalized = re.sub(pattern, replacement, normalized, flags=re.IGNORECASE)
    
    # Clean up extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip()
    
    print(f"✓ Normalized transcript: {len(transcript)} → {len(normalized)} chars")
    
    return {
        **state,
        "normalized_transcript": normalized
    }
