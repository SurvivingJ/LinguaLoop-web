import pytest

from services.concurrency import run_parallel


def test_results_keep_call_order():
    assert run_parallel(lambda: 1, lambda: 2, lambda: 3) == [1, 2, 3]


def test_exception_propagates():
    def boom():
        raise ValueError('x')
    with pytest.raises(ValueError):
        run_parallel(lambda: 1, boom)


def test_nested_calls_do_not_deadlock():
    def outer():
        return sum(run_parallel(lambda: 1, lambda: 2))
    assert run_parallel(*[outer] * 40) == [3] * 40
