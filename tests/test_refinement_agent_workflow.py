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


def test_repository_branch_and_user_testing_workflow_is_documented():
    dispatcher = Path(".github/agents/outdoor-ticket-dispatcher.agent.md").read_text()
    refinement = Path(".github/agents/outdoor-refinement.agent.md").read_text()
    coder = Path(".github/agents/outdoor-ticket-coder.agent.md").read_text()
    schema = Path("tickets/README.md").read_text()

    assert "select_ticket_repository" in refinement
    assert "default_target_branch" in refinement
    assert "create_working_branch" in dispatcher
    assert "finish_working_branch" in dispatcher
    assert "Do not update the ticket to `review` unless cleanup succeeds" in dispatcher
    assert "commits pending changes on the recorded" in dispatcher
    assert "checks out the recorded target branch without merging" in dispatcher
    assert "merge fails" in dispatcher
    assert "`review` -> `test`" in dispatcher
    assert "working_branch" in coder
    assert "`test`" in schema


def test_dispatcher_reads_plan_updates_before_annotations_or_dispatch():
    dispatcher = Path(".github/agents/outdoor-ticket-dispatcher.agent.md").read_text()
    normalized = " ".join(dispatcher.split())

    updates_step = dispatcher.index("### 1. Read the supplied plan updates")
    annotations_step = dispatcher.index("### 2. Process annotations after plan updates")
    dispatch_step = dispatcher.index("### 4. Dispatch ready tickets")

    assert updates_step < annotations_step < dispatch_step
    assert "plans/Sprint Review 24/voicechat-plan/plan-24-updates.md" in dispatcher
    assert "ready-to-paste Copilot Chat request" in dispatcher
    assert "acceptance" in dispatcher.lower()
    assert "Continue the workflow in this Copilot Chat conversation" in normalized


def test_dispatcher_creates_a_multi_file_markdown_review_without_audio():
    dispatcher = Path(".github/agents/outdoor-ticket-dispatcher.agent.md").read_text()
    readme = Path("README.md").read_text()

    assert "overview.md" in dispatcher
    assert "update-processing-record.md" in dispatcher
    assert "ticket-<ID>.md" in dispatcher
    assert "branch-diff-<ID>.md" in dispatcher
    assert "plan-N-updates.md" in dispatcher
    assert "Create" in dispatcher and "empty" in dispatcher
    assert "voicechat user" in dispatcher
    assert "combined.md" in dispatcher
    assert "do not generate or deploy audio" in dispatcher.lower()
    assert "synthesize_audio_plan" not in dispatcher
    assert "export_plan" not in dispatcher
    assert "create_next_plan_dir" not in dispatcher
    assert "multi-file Sprint Review package" in readme
    assert "not dispatcher requirements" in readme


def test_sprint_review_24_example_is_a_multi_file_markdown_package():
    package = Path("plans/Sprint Review 24/voicechat-plan")
    markdown_files = list(package.glob("*.md"))

    assert (package / "plan-24-updates.md").is_file()
    assert (package / "overview.md").is_file()
    assert (package / "update-processing-record.md").is_file()
    assert any(package.glob("ticket-*.md"))
    assert len(markdown_files) > 2
    assert not (package / "combined.md").exists()
    assert not list(package.rglob("*.wav"))
    assert not list(package.rglob("*.timing.json"))
