from app.services.adapters.executor_kinds import _extract_result_value_for_prompt


def test_extract_result_value_for_prompt_only_uses_value() -> None:
    value = _extract_result_value_for_prompt(
        {
            "value": "hello",
            "shell_type": "Codex",
            "resume_session_id": "thread_123",
            "retry_mode": "resume",
        }
    )
    assert value == "hello"


def test_extract_result_value_for_prompt_ignores_missing_value() -> None:
    value = _extract_result_value_for_prompt({"shell_type": "Codex"})
    assert value == ""
