import pytest


@pytest.fixture
async def enrolled_course(client, student_headers, course_factory):
    course, lessons, question = await course_factory()
    response = await client.post(f"/v1/courses/{course['id']}/enroll", headers=student_headers)
    assert response.status_code == 201, response.text
    return (course, lessons, question)


@pytest.fixture
async def finished_course(client, student_headers, learned_course):
    course, lessons, question = learned_course
    response = await client.post(
        f"/v1/lessons/{lessons[1]['id']}/complete", headers=student_headers
    )
    assert response.status_code == 200, response.text
    return (learned_course, response.json())
