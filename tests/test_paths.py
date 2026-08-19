from phiexplorer.paths import data_root, repo_root


def test_repo_root_is_package_parent():
    root = repo_root()
    assert (root / "phiexplorer").is_dir()
    assert (root / "pyproject.toml").is_file()


def test_data_root_default(monkeypatch):
    monkeypatch.delenv("PHI_DATA_ROOT", raising=False)
    root = data_root()
    assert root.name == "phi-explorer-data"
    assert root.parent == repo_root().parent


def test_data_root_override(monkeypatch, tmp_path):
    monkeypatch.setenv("PHI_DATA_ROOT", str(tmp_path))
    assert data_root() == tmp_path.resolve()
