from pathlib import Path

from phiexplorer.cli import main

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_export.json"


def test_organisms_lists_all_organisms(capsys):
    exit_code = main(["--input", str(FIXTURE_PATH), "organisms"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "90000\tTestus pathogenicus" in out
    assert "90001\tTestus hostus" in out


def test_summary_writes_report(tmp_path, capsys):
    exit_code = main(
        ["--input", str(FIXTURE_PATH), "summary", "--output-dir", str(tmp_path)]
    )
    assert exit_code == 0
    out_path = Path(capsys.readouterr().out.strip())
    assert out_path.exists()
    assert out_path.parent == tmp_path


def test_bad_input_path_errors_cleanly(capsys):
    exit_code = main(["--input", "/nonexistent/export.json", "organisms"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
