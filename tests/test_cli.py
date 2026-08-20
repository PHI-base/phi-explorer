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


def test_phenotypes_writes_report_by_taxid(tmp_path, capsys):
    exit_code = main(
        [
            "--input", str(FIXTURE_PATH),
            "phenotypes", "--taxid", "90000", "--output-dir", str(tmp_path),
        ]
    )
    assert exit_code == 0
    out_path = Path(capsys.readouterr().out.strip())
    assert out_path.exists()


def test_phenotypes_writes_report_by_sciname(tmp_path, capsys):
    exit_code = main(
        [
            "--input", str(FIXTURE_PATH),
            "phenotypes", "--sciname", "Testus pathogenicus", "--output-dir", str(tmp_path),
        ]
    )
    assert exit_code == 0
    out_path = Path(capsys.readouterr().out.strip())
    assert out_path.exists()


def test_effectors_writes_report(tmp_path, capsys):
    exit_code = main(
        [
            "--input", str(FIXTURE_PATH),
            "effectors", "--taxid", "90000", "--output-dir", str(tmp_path),
        ]
    )
    assert exit_code == 0
    out_path = Path(capsys.readouterr().out.strip())
    assert out_path.exists()


def test_organism_summary_prints_counts(capsys):
    exit_code = main(["--input", str(FIXTURE_PATH), "organism-summary", "--taxid", "90000"])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert "genes\t2" in out
    assert "interactions\t2" in out


def test_unresolvable_taxid_errors_cleanly(capsys):
    exit_code = main(["--input", str(FIXTURE_PATH), "phenotypes", "--taxid", "1"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")


def test_missing_organism_args_errors_cleanly(capsys):
    exit_code = main(["--input", str(FIXTURE_PATH), "phenotypes"])
    assert exit_code == 1
    err = capsys.readouterr().err
    assert "must provide" in err


def test_mismatched_taxid_sciname_errors_cleanly(capsys):
    exit_code = main(
        [
            "--input", str(FIXTURE_PATH),
            "phenotypes", "--taxid", "90000", "--sciname", "Testus hostus",
        ]
    )
    assert exit_code == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
