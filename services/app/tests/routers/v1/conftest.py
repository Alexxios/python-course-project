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
