from app.services.adapters.executor_kinds import ExecutorKindsService


def test_calculate_task_progress_converges_on_final_states():
    assert (
        ExecutorKindsService._calculate_task_progress(
            total_subtasks=1,
            completed_subtasks=0,
            running_progress=0,
            previous_progress=10,
            status="COMPLETED",
        )
        == 100
    )
    assert (
        ExecutorKindsService._calculate_task_progress(
            total_subtasks=1,
            completed_subtasks=0,
            running_progress=0,
            previous_progress=10,
            status="FAILED",
        )
        == 100
    )
    assert (
        ExecutorKindsService._calculate_task_progress(
            total_subtasks=1,
            completed_subtasks=0,
            running_progress=0,
            previous_progress=10,
            status="CANCELLED",
        )
        == 100
    )


def test_calculate_task_progress_uses_running_progress_as_fractional_step():
    # 2 subtasks: 1 completed, 1 running at 50% => (1 + 0.5) / 2 * 100 = 75
    assert (
        ExecutorKindsService._calculate_task_progress(
            total_subtasks=2,
            completed_subtasks=1,
            running_progress=50,
            previous_progress=0,
            status="RUNNING",
        )
        == 75
    )


def test_calculate_task_progress_pseudo_increases_when_running_progress_is_missing():
    # No running progress: should monotonically bump but cap below 100.
    p1 = ExecutorKindsService._calculate_task_progress(
        total_subtasks=1,
        completed_subtasks=0,
        running_progress=0,
        previous_progress=10,
        status="RUNNING",
    )
    assert p1 == 11

    # Cap at 90% for a single running step (0.9 / 1 * 100)
    p2 = ExecutorKindsService._calculate_task_progress(
        total_subtasks=1,
        completed_subtasks=0,
        running_progress=0,
        previous_progress=89,
        status="RUNNING",
    )
    assert p2 == 90


def test_calculate_task_progress_never_goes_backward():
    # If executor reports 0 after previously higher progress, keep previous.
    assert (
        ExecutorKindsService._calculate_task_progress(
            total_subtasks=1,
            completed_subtasks=0,
            running_progress=0,
            previous_progress=50,
            status="RUNNING",
        )
        == 51
    )

    assert (
        ExecutorKindsService._calculate_task_progress(
            total_subtasks=1,
            completed_subtasks=0,
            running_progress=10,
            previous_progress=50,
            status="RUNNING",
        )
        == 50
    )


def test_calculate_task_progress_caps_running_at_99():
    assert (
        ExecutorKindsService._calculate_task_progress(
            total_subtasks=1,
            completed_subtasks=0,
            running_progress=100,
            previous_progress=0,
            status="RUNNING",
        )
        == 99
    )
