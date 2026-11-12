"""API v1 contracts: student responses never include passwords or answer keys."""

from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
)


def safe_text(value: str) -> str:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Use valid Unicode text") from exc
    if "\x00" in value:
        raise ValueError("NUL characters are not allowed")
    return value


def utf8_secret(value: SecretStr) -> SecretStr:
    try:
        value.get_secret_value().encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Use valid Unicode text") from exc
    return value


Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    AfterValidator(safe_text),
]

Username = Annotated[str, StringConstraints(to_lower=True, pattern=r"^[a-zA-Z0-9_]{3,50}$")]

Password = Annotated[SecretStr, Field(min_length=12, max_length=128), AfterValidator(utf8_secret)]

Credential = Annotated[SecretStr, Field(min_length=1, max_length=128), AfterValidator(utf8_secret)]


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)


class Register(Schema):
    username: Username
    first_name: Name
    last_name: Name
    password: Password


class Login(Schema):
    username: Username
    password: Credential


class UserView(Schema):
    id: int
    username: str
    first_name: str
    last_name: str
    role: Literal["student", "admin"]
    created_at: int


class Tokens(Schema):
    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int


class Refresh(Schema):
    refresh_token: Annotated[str, Field(min_length=1, max_length=256), AfterValidator(safe_text)]


class ChangePassword(Schema):
    current_password: Credential
    new_password: Password
