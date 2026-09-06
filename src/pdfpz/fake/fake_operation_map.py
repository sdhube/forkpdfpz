"""fake_operation_map.py -- a test-double operation_map for exercising
BookOperationPlan.run_plan() without calling any real BooksActions
method. Each fake operation just appends its own flag name to a shared
call_order list, so a caller can assert on the actual order run_plan()
called stages in.

Started life as an ad-hoc verification script run once, by hand, to
check run_plan()'s two non-DB sequences (full run, explicit
first_stage) before committing it; moved here so that same check is
reusable/re-runnable instead of a one-off snippet.
"""

from typing import Callable, Dict, List

from pdfpz.core.class_book_operations import BookOperationPlan, BookOperationStage


def make_fake_operation_map(call_order: List[str]) -> Dict[str, Callable[[], None]]:
    """One fake callable per BookOperationStage, keyed by operation_flag
    (same shape cli.py's real operation_map has). Calling any of them
    appends that stage's operation_flag to call_order -- nothing else.
    """
    return {
        stage.operation_flag: (lambda flag=stage.operation_flag: call_order.append(flag))
        for stage in BookOperationStage.canonical_order()
    }


def verify_full_run() -> None:
    """Every stage should run, in canonical order, when first_stage is
    omitted."""
    call_order: List[str] = []
    operation_map = make_fake_operation_map(call_order)

    state = BookOperationPlan.run_plan(operation_map)

    expected = [stage.operation_flag for stage in BookOperationStage.canonical_order()]
    assert call_order == expected, call_order
    assert state.is_finished()
    print("full run: all 11 stages called in order:", call_order)


def verify_from_stage() -> None:
    """Only first_stage onward should run, in canonical order, when
    first_stage is given."""
    call_order: List[str] = []
    operation_map = make_fake_operation_map(call_order)

    state = BookOperationPlan.run_plan(operation_map, first_stage=BookOperationStage.F_SANITIZE_INFO)

    expected = [stage.operation_flag for stage in BookOperationStage.canonical_order()[5:]]
    assert call_order == expected, call_order
    assert state.is_finished()
    assert len(state.stages) == 6
    print("from-stage run: only F_SANITIZE_INFO onward called:", call_order)


if __name__ == "__main__":
    verify_full_run()
    verify_from_stage()
    print("ALL GOOD")
