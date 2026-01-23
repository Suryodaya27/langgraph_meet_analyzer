"""
LangGraph Workflow for Fact-First Meeting Processing
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
from datetime import datetime

# Import nodes
from src2.nodes.normalize import normalize_transcript
from src2.nodes.extract_facts import extract_facts
from src2.nodes.validate_facts import validate_facts
from src2.nodes.generate_summary import generate_summary
from src2.nodes.generate_action_points import generate_action_points
from src2.nodes.generate_todos import generate_todos
from src2.nodes.generate_email import generate_email
from src2.nodes.compliance_check import compliance_check


# State type for LangGraph
class GraphState(TypedDict):
    raw_transcript: str
    normalized_transcript: str
    extracted_facts: dict
    validated_facts: dict
    summary: str
    action_points: list
    todos: list
    follow_up_emails: list
    outputs: dict
    compliance_passed: bool
    compliance_issues: list
    processing_started: str
    processing_completed: str


def assemble_outputs(state):
    """Assemble all generated outputs into final MeetingOutputs object"""
    from src2.models import MeetingOutputs
    
    outputs = MeetingOutputs(
        summary=state.get("summary", "No summary generated"),
        action_points=state.get("action_points", []),
        todos=state.get("todos", []),
        follow_up_emails=state.get("follow_up_emails", []),
        total_facts_extracted=(
            len(state["extracted_facts"].decisions) + 
            len(state["extracted_facts"].action_items) +
            len(state["extracted_facts"].open_questions) +
            len(state["extracted_facts"].deadlines) +
            len(state["extracted_facts"].metrics)
        ),
        total_facts_validated=len(state["validated_facts"].facts),
        facts_discarded=state["validated_facts"].discarded_count
    )
    
    print(f"\n✓ Assembled final outputs:")
    print(f"  - Summary: {len(outputs.summary)} chars")
    print(f"  - Action Points: {len(outputs.action_points)}")
    print(f"  - Todos: {len(outputs.todos)}")
    print(f"  - Emails: {len(outputs.follow_up_emails)}")
    
    return {**state, "outputs": outputs}


def create_workflow(llm):
    """
    Create the fact-first processing workflow.
    
    Flow:
    1. Normalize → 2. Extract Facts → 3. Validate Facts → 
    4. Generate Summary → 5. Generate Action Points → 6. Generate Todos → 
    7. Generate Email → 8. Assemble Outputs → 9. Compliance Check → END
    
    Each generation step does ONE thing with simple JSON.
    """
    
    # Create graph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("normalize", normalize_transcript)
    workflow.add_node("extract_facts", lambda state: extract_facts(state, llm))
    workflow.add_node("validate_facts", validate_facts)
    workflow.add_node("generate_summary", lambda state: generate_summary(state, llm))
    workflow.add_node("generate_action_points", lambda state: generate_action_points(state, llm))
    workflow.add_node("generate_todos", lambda state: generate_todos(state, llm))
    workflow.add_node("generate_email", lambda state: generate_email(state, llm))
    workflow.add_node("assemble_outputs", assemble_outputs)
    workflow.add_node("compliance_check", compliance_check)
    
    # Define edges (linear flow)
    workflow.set_entry_point("normalize")
    workflow.add_edge("normalize", "extract_facts")
    workflow.add_edge("extract_facts", "validate_facts")
    workflow.add_edge("validate_facts", "generate_summary")
    workflow.add_edge("generate_summary", "generate_action_points")
    workflow.add_edge("generate_action_points", "generate_todos")
    workflow.add_edge("generate_todos", "generate_email")
    workflow.add_edge("generate_email", "assemble_outputs")
    workflow.add_edge("assemble_outputs", "compliance_check")
    workflow.add_edge("compliance_check", END)
    
    # Compile
    app = workflow.compile()
    
    return app


def process_meeting_v8(transcript: str, llm) -> dict:
    """
    Process meeting using fact-first architecture.
    
    Args:
        transcript: Raw meeting transcript
        llm: LLM instance
    
    Returns:
        Final outputs with metadata
    """
    
    print("\n" + "="*70)
    print("FACT-FIRST MEETING PROCESSOR V8")
    print("="*70)
    print("Architecture: Extract → Validate → Derive")
    print("="*70 + "\n")
    
    # Create workflow
    app = create_workflow(llm)
    
    # Initial state
    initial_state = {
        "raw_transcript": transcript,
        "processing_started": datetime.now().isoformat()
    }
    
    # Run workflow
    try:
        final_state = app.invoke(initial_state)
        
        final_state["processing_completed"] = datetime.now().isoformat()
        
        print("\n" + "="*70)
        print("PROCESSING COMPLETE")
        print("="*70)
        outputs = final_state['outputs']
        print(f"Facts Extracted: {outputs.total_facts_extracted}")
        print(f"Facts Validated: {outputs.total_facts_validated}")
        print(f"Facts Discarded: {outputs.facts_discarded}")
        print(f"Compliance: {'✓ PASSED' if final_state['compliance_passed'] else '✗ FAILED'}")
        print("="*70 + "\n")
        
        return final_state
        
    except Exception as e:
        print(f"\n✗ Processing failed: {e}")
        raise
