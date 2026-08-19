from phiexplorer.smoke import run_benchmark_check


def test_run_benchmark_check_skips_when_data_absent(monkeypatch, tmp_path):
    monkeypatch.setenv("PHI_DATA_ROOT", str(tmp_path))
    assert run_benchmark_check() is True
