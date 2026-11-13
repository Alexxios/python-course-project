import pytest
from fastapi import HTTPException
from hypothesis import given
from hypothesis import strategies as st

from app.learning import grade_answers
from app.schemas import Submission

pytestmark = pytest.mark.fuzz


@given(answers=st.lists(st.integers(min_value=0, max_value=1), min_size=1, max_size=100))
def test_grading_matches_the_number_of_correct_answers(answers):
    questions = [
        {"id": index, "options": ["correct", "wrong"], "correct_option": 0}
        for index in range(1, len(answers) + 1)
    ]
    submission = Submission(
        answers=[
            {"question_id": index, "option": answer} for index, answer in enumerate(answers, 1)
        ]
    )
    correct, score = grade_answers(questions, submission)
    assert correct == answers.count(0)
    assert score == round(100 * answers.count(0) / len(answers), 2)


@given(identity=st.integers(min_value=2, max_value=2147483647))
def test_submissions_cannot_reference_questions_outside_the_test(identity):
    with pytest.raises(HTTPException) as exc:
        grade_answers(
            [{"id": 1, "options": ["A", "B"], "correct_option": 0}],
            Submission(answers=[{"question_id": identity, "option": 0}]),
        )
    assert exc.value.status_code == 422
