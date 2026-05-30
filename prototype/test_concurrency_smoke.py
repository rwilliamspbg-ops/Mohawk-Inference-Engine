import os
import pytest
from prototype.load_harness import run_load


def test_concurrency_smoke():
    # integration smoke test: only run when RUN_INTEGRATION=1 is set
    if os.environ.get('RUN_INTEGRATION') != '1':
        pytest.skip('integration tests disabled')
    # expect a running worker on 127.0.0.1:8003
    workers = ["http://127.0.0.1:8003"]
    # small smoke run
    res = run_load(workers, concurrency=2, total=4, encrypt=True)
    assert len(res) == 4
