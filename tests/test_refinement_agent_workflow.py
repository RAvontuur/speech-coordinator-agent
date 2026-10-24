from pathlib import Path


def test_dispatcher_and_refinement_agents_are_configured():
    dispatcher = Path(".github/agents/outdoor-ticket-dispatcher.agent.md").read_text()
    refinement = Path(".github/agents/outdoor-refinement.agent.md")

    assert "Outdoor Refinement" in dispatcher
    assert "refinement" in dispatcher.lower()
    assert refinement.exists()

    refinement_text = refinement.read_text()
    assert "Outdoor Refinement" in refinement_text
    assert "refine" in refinement_text.lower()
    assert "update_ticket" in refinement_text or "transition_ticket" in refinement_text


def test_dispatcher_supports_annotation_state_transitions_and_history_preservation():
    dispatcher = Path(".github/agents/outdoor-ticket-dispatcher.agent.md").read_text()
    schema = Path("tickets/README.md").read_text()

    assert "annotation" in dispatcher.lower()
    assert "transition_ticket" in dispatcher
    assert "decision_evidence" in dispatcher or "evidence" in dispatcher
    assert "keep a ticket in `review`" in schema or "History" in schema
    assert "Do not change ticket state in response to annotations" not in dispatcher
