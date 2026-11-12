import pytest

pytestmark = pytest.mark.anyio


@pytest.mark.parametrize(
    "changes",
    [
        {"options": ["same", "same"]},
        {"options": ["only"]},
        {"correct_option": 2},
        {"correct_option": True},
        {"position": 0},
        {"prompt": " "},
        {"options": ["x"] * 7},
    ],
)
async def test_invalid_test_definitions(client, admin_headers, course_factory, changes):
    _, lessons, _ = await course_factory(published=False, with_test=False)
    payload = {"prompt": "Question", "options": ["A", "B"], "correct_option": 0, "position": 1}
    assert (
        await client.post(
            f"/v1/admin/lessons/{lessons[0]['id']}/questions",
            headers=admin_headers,
            json=payload | changes,
        )
    ).status_code == 422
