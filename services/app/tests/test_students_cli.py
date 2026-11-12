import json
from pathlib import Path

import pytest

from app.students.__main__ import main


def test_cli_workflow(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("STUDENTS_DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    main(["init-db"])
    assert json.loads(capsys.readouterr().out) == {"status": "ready"}
    main(["import-csv", str(Path(__file__).parents[1] / "examples" / "students.csv")])
    assert json.loads(capsys.readouterr().out) == {"imported": 215}
    main(["students", "--faculty", "АВТФ"])
    assert len(json.loads(capsys.readouterr().out)) == 10
    main(["courses"])
    assert len(json.loads(capsys.readouterr().out)) == 6
    main(["low-grades", "--course", "Мат. Анализ"])
    assert json.loads(capsys.readouterr().out)
    main(["average", "--faculty", "ФПМИ"])
    assert json.loads(capsys.readouterr().out) == {"faculty": "ФПМИ", "average_grade": 49.225}


def test_cli_reports_missing_schema_without_traceback(tmp_path, capsys):
    with pytest.raises(SystemExit, match="1"):
        main(["--database-url", f"sqlite:///{tmp_path / 'uninitialized.db'}", "courses"])
    assert "run init-db" in capsys.readouterr().err


def test_cli_reports_missing_file(tmp_path, capsys):
    with pytest.raises(SystemExit, match="1"):
        main(["--database-url", "sqlite://", "import-csv", str(tmp_path / "missing.csv")])
    assert "missing.csv" in capsys.readouterr().err
