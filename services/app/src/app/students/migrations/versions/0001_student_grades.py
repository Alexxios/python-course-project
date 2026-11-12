"""Create student grade records without deduplicating source observations."""

import sqlalchemy as sa
from alembic import op

revision = "0001_student_grades"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "student_grades",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("last_name", sa.String(200), nullable=False),
        sa.Column("first_name", sa.String(200), nullable=False),
        sa.Column("faculty", sa.String(200), nullable=False),
        sa.Column("course", sa.String(200), nullable=False),
        sa.Column("grade", sa.Integer(), nullable=False),
        sa.CheckConstraint("grade >= 0 AND grade <= 100", name="ck_student_grades_grade"),
        *(
            sa.CheckConstraint(
                f"length(trim({column})) > 0 AND length({column}) <= 200",
                name=f"ck_student_grades_{column}",
            )
            for column in ("last_name", "first_name", "faculty", "course")
        ),
    )
    op.create_index("ix_student_grades_faculty", "student_grades", ["faculty"])
    op.create_index("ix_student_grades_course_grade", "student_grades", ["course", "grade"])


def downgrade() -> None:
    op.drop_index("ix_student_grades_course_grade", table_name="student_grades")
    op.drop_index("ix_student_grades_faculty", table_name="student_grades")
    op.drop_table("student_grades")
