"""Validated subscriber appeals and their persisted representation."""

import re
import unicodedata
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Annotated
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field, field_validator


class AppealReason(StrEnum):
    NO_NETWORK = "нет доступа к сети"
    PHONE_NOT_WORKING = "не работает телефон"
    EMAIL_NOT_RECEIVED = "не приходят письма"


class AppealCreate(BaseModel):
    """One subscriber and one or more reasons for contacting support."""

    model_config = ConfigDict(extra="forbid")

    last_name: Annotated[str, Field(min_length=1, description="Cyrillic, uppercase initial")]
    first_name: Annotated[str, Field(min_length=1, description="Cyrillic, uppercase initial")]
    birth_date: date = Field(description="YYYY-MM-DD, no later than today (UTC)")
    phone: Annotated[
        str,
        Field(pattern=r"^\+[1-9][0-9]{7,14}$", description="+ followed by 8 to 15 digits"),
    ]
    email: EmailStr
    reasons: Annotated[list[AppealReason], Field(min_length=1)]
    detected_at: AwareDatetime = Field(
        description="ISO 8601 date and time with a UTC offset; cannot be in the future"
    )

    @field_validator("last_name", "first_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value[0].isupper() or not all(
            char.isalpha() and "CYRILLIC" in unicodedata.name(char, "") for char in value
        ):
            raise ValueError("Use only Cyrillic letters, starting with an uppercase letter")
        return value

    @field_validator("birth_date", mode="before")
    @classmethod
    def validate_birth_date_format(cls, value: object) -> object:
        if type(value) is date:
            return value
        if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
            raise ValueError("Use a date in YYYY-MM-DD format")
        return value

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, value: date) -> date:
        if value > datetime.now(UTC).date():
            raise ValueError("Birth date cannot be in the future")
        return value

    @field_validator("detected_at", mode="before")
    @classmethod
    def validate_detection_format(cls, value: object) -> object:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or "T" not in value:
            raise ValueError("Use an ISO 8601 datetime with T and a UTC offset")
        return value

    @field_validator("detected_at")
    @classmethod
    def validate_detection_time(cls, value: datetime) -> datetime:
        if value > datetime.now(UTC):
            raise ValueError("Detection time cannot be in the future")
        return value


class StoredAppeal(AppealCreate):
    """An accepted appeal, identified by its JSON filename."""

    id: UUID = Field(default_factory=uuid4)
