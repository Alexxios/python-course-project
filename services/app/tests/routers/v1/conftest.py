import pytest

from app.models import User
from app.security import PASSWORD_HASH

TEST_PASSWORD = "correct horse battery staple"
TEST_HASH = PASSWORD_HASH.hash(TEST_PASSWORD)


@pytest.fixture
def password():
    return TEST_PASSWORD


@pytest.fixture
def account_factory(client, application):

    async def create(username="student", role="student"):
        async with application.state.sessions.begin() as db:
            user = User(
                username=username,
                first_name="Иван",
                last_name="Ли",
                password_hash=TEST_HASH,
                role=role,
            )
            db.add(user)
            await db.flush()
            identity = user.id
        response = await client.post(
            "/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}
        )
        assert response.status_code == 200, response.text
        tokens = response.json()
        return (identity, {"Authorization": f"Bearer {tokens['access_token']}"}, tokens)

    return create


@pytest.fixture
async def admin_headers(account_factory):
    return (await account_factory("admin", "admin"))[1]


@pytest.fixture
async def student_headers(account_factory):
    return (await account_factory())[1]


@pytest.fixture
def course_factory(client, admin_headers):

    async def create(title="Python", published=True, with_test=True):
        response = await client.post(
            "/v1/admin/courses",
            headers=admin_headers,
            json={"title": title, "description": "Learn Python"},
        )
        assert response.status_code == 201, response.text
        course = response.json()
        lessons = []
        for position in [10, 20]:
            response = await client.post(
                f"/v1/admin/courses/{course['id']}/lessons",
                headers=admin_headers,
                json={
                    "title": f"Lesson {position}",
                    "position": position,
                    "content": "Python lists are mutable. Tuples are immutable.",
                },
            )
            assert response.status_code == 201, response.text
            lessons.append(response.json())
        question = None
        if with_test:
            response = await client.post(
                f"/v1/admin/lessons/{lessons[0]['id']}/questions",
                headers=admin_headers,
                json={
                    "prompt": "Which Python collection is mutable?",
                    "options": ["list", "tuple"],
                    "correct_option": 0,
                    "position": 1,
                },
            )
            assert response.status_code == 201, response.text
            question = response.json()
        if published:
            response = await client.put(
                f"/v1/admin/courses/{course['id']}",
                headers=admin_headers,
                json={"title": title, "description": "Learn Python", "published": True},
            )
            assert response.status_code == 200, response.text
            course = response.json()
        return (course, lessons, question)

    return create
