"""Exercise the required queries against migrated SQL databases and the supplied CSV."""

import csv
from pathlib import Path

import pytest
from sqlalchemy import insert
from sqlalchemy.exc import IntegrityError

from app.students.models import StudentGrade
from app.students.schemas import GradeCreate

DATASET = Path(__file__).parents[1] / "examples" / "students.csv"
HEADER = "Фамилия,Имя,Факультет,Курс,Оценка\n"


def test_supplied_dataset_is_preserved(student_repository):
    assert student_repository.import_csv(DATASET) == 215
    with DATASET.open(encoding="utf-8") as stream:
        expected = [
            (r["Фамилия"], r["Имя"], r["Факультет"], r["Курс"], int(r["Оценка"]))
            for r in csv.DictReader(stream)
        ]
    actual = student_repository.select_all()
    assert [(r.last_name, r.first_name, r.faculty, r.course, r.grade) for r in actual] == expected
    assert len({r.id for r in actual}) == 215
    assert student_repository.unique_courses() == [
        "Информатика",
        "История",
        "Мат. Анализ",
        "Психология",
        "Теор. Механика",
        "Физика",
    ]
    for faculty, count, average in [
        ("АВТФ", 10, 56.836363636363636),
        ("РЭФ", 7, 50.95454545454545),
        ("ФЛА", 10, 42.723404255319146),
        ("ФПМИ", 8, 49.225),
        ("ФТФ", 10, 49.72549019607843),
    ]:
        assert len(student_repository.students_by_faculty(faculty)) == count
        assert student_repository.average_grade_by_faculty(faculty) == pytest.approx(average)
    # Import is intentionally append-only, including exact duplicates in the source.
    assert student_repository.import_csv(DATASET) == 215
    assert len(student_repository.select_all()) == 430


def test_queries_distinguish_faculties_and_use_strict_grade_boundary(student_repository):
    for last_name, faculty, course, grade in [
        ("Ли", "А", "Математика", 0),
        ("Ли", "А", "Математика", 29),
        ("Ли", "Б", "Математика", 100),
        ("Ким", "А", "Математика", 30),
        ("Ким", "А", "Физика", 10),
    ]:
        student_repository.insert(
            GradeCreate(
                last_name=last_name, first_name="Иван", faculty=faculty, course=course, grade=grade
            )
        )
    assert [s.last_name for s in student_repository.students_below_30("Математика")] == ["Ли"]
    students = student_repository.students_by_faculty("А")
    assert [(s.last_name, s.faculty) for s in students] == [("Ким", "А"), ("Ли", "А")]
    assert student_repository.average_grade_by_faculty("А") == pytest.approx(17.25)
    assert student_repository.average_grade_by_faculty("Б") == 100


def test_empty_and_unknown_filters(student_repository):
    assert student_repository.select_all() == []
    assert student_repository.unique_courses() == []
    assert student_repository.students_by_faculty("Unknown") == []
    assert student_repository.students_below_30("Unknown") == []
    assert student_repository.average_grade_by_faculty("Unknown") is None


@pytest.mark.parametrize(
    "bad_row",
    [
        "Ли,Иван,АВТФ,Физика,-1\n",
        "Ли,Иван,АВТФ,Физика,101\n",
        "Ли,Иван,АВТФ,Физика,29.5\n",
        "Ли,Иван,АВТФ,Физика,abc\n",
        "Ли,Иван,АВТФ,Физика,\n",
        ",Иван,АВТФ,Физика,20\n",
        "Ли,Иван, ,Физика,20\n",
        "Ли,Иван,АВТФ,Физика\n",
        "Ли,Иван,АВТФ,Физика,20,extra\n",
        '"Ли,Иван,АВТФ,Физика,20\n',
    ],
)
def test_bad_late_csv_row_rolls_back_only_this_import(
    student_repository, grade_payload, tmp_path, bad_row
):
    original = student_repository.insert(GradeCreate(**grade_payload))
    source = tmp_path / "invalid.csv"
    source.write_text(HEADER + "Ким,Петр,ФПМИ,История,40\n" + bad_row, encoding="utf-8")
    with pytest.raises(ValueError, match="CSV line 3"):
        student_repository.import_csv(source)
    assert student_repository.select_all() == [original]


@pytest.mark.parametrize(
    "content",
    [
        "",
        "last_name,first_name,faculty,course,grade\n",
        "Фамилия,Имя,Факультет,Курс,Курс\n",
        "Фамилия,Имя,Факультет,Курс,Оценка,Лишнее\n",
    ],
)
def test_csv_requires_exact_headers(student_repository, tmp_path, content):
    source = tmp_path / "headers.csv"
    source.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError, match="CSV headers"):
        student_repository.import_csv(source)
    assert student_repository.select_all() == []


def test_csv_supports_bom_reordered_headers_quoting_and_empty_files(student_repository, tmp_path):
    source = tmp_path / "students.csv"
    source.write_text(HEADER, encoding="utf-8-sig")
    assert student_repository.import_csv(source) == 0
    source.write_text(
        'Оценка,Курс,Факультет,Имя,Фамилия\n29,"Физика, часть 1",АВТФ,Иван,Ли\n',
        encoding="utf-8-sig",
    )
    assert student_repository.import_csv(source) == 1
    assert student_repository.unique_courses() == ["Физика, часть 1"]


def test_malformed_csv_header_reports_its_line(student_repository, tmp_path):
    source = tmp_path / "invalid.csv"
    source.write_text('"Фамилия,Имя,Факультет,Курс,Оценка\n', encoding="utf-8")
    with pytest.raises(ValueError, match="CSV line 1: malformed CSV"):
        student_repository.import_csv(source)


def test_filters_are_literal_values(student_repository, grade_payload):
    student_repository.insert(GradeCreate(**grade_payload))
    assert student_repository.students_by_faculty("АВТФ' OR 1=1 --") == []
    assert student_repository.students_below_30("%") == []
    assert student_repository.average_grade_by_faculty("' OR 1=1 --") is None


@pytest.mark.parametrize(
    "changes", [{"grade": -1}, {"grade": 101}, {"faculty": ""}, {"course": None}]
)
def test_database_constraints_apply_without_pydantic(student_engine, grade_payload, changes):
    with pytest.raises(IntegrityError), student_engine.begin() as connection:
        connection.execute(insert(StudentGrade).values(**(grade_payload | changes)))
