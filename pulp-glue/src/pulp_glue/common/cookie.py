import datetime
import typing as t
from email.utils import parsedate_to_datetime

from pydantic import BaseModel, field_validator, type_adapter


def _kv_split(crumble: str) -> tuple[str, str]:
    try:
        key, value = crumble.split("=", maxsplit=1)
    except ValueError:
        key = crumble
        value = ""
    return key, value


class Cookie(BaseModel):
    name: str
    value: str
    expires: datetime.datetime | None = None

    @field_validator("expires", mode="before")
    @classmethod
    def parse_expires(cls, value: str | datetime.datetime) -> datetime.datetime | str:
        if isinstance(value, str):
            try:
                return parsedate_to_datetime(value)
            except ValueError:
                pass
        return value

    @classmethod
    def from_header(cls, cookie_desc: str) -> t.Self:
        crumbles = [_kv_split(crumble.strip()) for crumble in cookie_desc.split(";")]
        name, value = crumbles[0]
        return cls(name=name, value=value, **dict(crumbles[1:]))


cookiejar_adapter = type_adapter.TypeAdapter(list[Cookie])
