import pytest
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
