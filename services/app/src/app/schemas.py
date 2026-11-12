"""API v1 contracts: student responses never include passwords or answer keys."""

from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    SecretStr,
    StringConstraints,
    model_validator,
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


Text = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=200),
    AfterValidator(safe_text),
]

Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    AfterValidator(safe_text),
]

Description = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=5000), AfterValidator(safe_text)
]

Content = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=50000),
    AfterValidator(safe_text),
]

Username = Annotated[str, StringConstraints(to_lower=True, pattern=r"^[a-zA-Z0-9_]{3,50}$")]

Password = Annotated[SecretStr, Field(min_length=12, max_length=128), AfterValidator(utf8_secret)]

Credential = Annotated[SecretStr, Field(min_length=1, max_length=128), AfterValidator(utf8_secret)]

PositiveInt = Annotated[int, Field(strict=True, ge=1, le=2147483647)]

Search = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=200), AfterValidator(safe_text)
]


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


class CourseCreate(Schema):
    title: Text
    description: Description = ""
    passing_score: Annotated[int, Field(strict=True, ge=1, le=100)] = 70


class CourseUpdate(CourseCreate):
    published: bool = False


class CourseView(CourseUpdate):
    id: int
    author_id: int
    created_at: int


class LessonWrite(Schema):
    title: Text
    description: Description = ""
    content: Content
    position: PositiveInt
    video_url: HttpUrl | None = None


class LessonView(Schema):
    id: int
    course_id: int
    title: str
    description: str
    content: str
    position: int
    video_url: str | None


class QuestionWrite(Schema):
    prompt: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=2000),
        AfterValidator(safe_text),
    ]
    options: Annotated[list[Text], Field(min_length=2, max_length=6)]
    correct_option: Annotated[int, Field(strict=True, ge=0, le=5)]
    position: PositiveInt

    @model_validator(mode="after")
    def validate_choices(self) -> Self:
        if self.correct_option >= len(self.options):
            raise ValueError("correct_option must identify an existing option (zero-based)")
        if len(set(self.options)) != len(self.options):
            raise ValueError("Answer options must be distinct")
        return self


class QuestionView(QuestionWrite):
    id: int
    lesson_id: int


class Page[T](Schema):
    items: list[T]
    total: int
    limit: int
    offset: int
