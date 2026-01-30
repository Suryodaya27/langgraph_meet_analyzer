"""
Step 1: Normalize Transcript
Clean and prepare transcript for fact extraction
"""

import re
from typing import Dict, Any


def normalize_transcript(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize the transcript for better extraction.
    
    - Remove filler words
    - Normalize whitespace
    - Keep speaker labels intact
    """
    
    transcript = state["raw_transcript"]
    original_length = len(transcript)
    
    # Remove common filler words (but keep meaning)
    fillers = [
        r'\b(um|uh|er|ah|like,|you know,|basically,|actually,|literally,)\b',
        r'\s+',  # Multiple spaces to single
    ]
    
    normalized = transcript
    for pattern in fillers:
        if pattern == r'\s+':
            normalized = re.sub(pattern, ' ', normalized)
        else:
            normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)
    
    # Clean up any double spaces created
    normalized = re.sub(r' +', ' ', normalized)
    normalized = normalized.strip()
    
    print(f"✓ Normalized transcript: {original_length} → {len(normalized)} chars")
    
    return {
        **state,
        "normalized_transcript": normalized
    }
