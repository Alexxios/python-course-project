import pytest
from fastapi import HTTPException
from hypothesis import given
from hypothesis import strategies as st

from app.learning import grade_answers
from app.schemas import Submission

pytestmark = pytest.mark.fuzz


@given(identity=st.integers(min_value=2, max_value=2147483647))
def test_submissions_cannot_reference_questions_outside_the_test(identity):
    with pytest.raises(HTTPException) as exc:
        grade_answers(
            [{"id": 1, "options": ["A", "B"], "correct_option": 0}],
            Submission(answers=[{"question_id": identity, "option": 0}]),
        )
    assert exc.value.status_code == 422
