import datetime
import typing as t
from email.utils import parsedate_to_datetime

from pydantic import BaseModel, field_validator, type_adapter
from pydantic.alias_generators import to_snake


def _kv_split(crumble: str) -> tuple[str, str | bool]:
    try:
        key, value = crumble.split("=", maxsplit=1)
    except ValueError:
        return to_snake(crumble), True
    return to_snake(key), value


class Cookie(BaseModel):
    name: str
    value: str
    domain: str | None = None
    expires: datetime.datetime | None = None
    http_only: bool = False
    path: str | None = None
    same_site: t.Literal["Strict", "Lax", "None"] | None = None
    secure: bool = False

    # TODO add url to prevent cross-site shenanigans

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
        crumbles = [crumble.strip() for crumble in cookie_desc.split(";")]
        name, value = crumbles[0].split("=", maxsplit=1)
        attributes = {k: v for k, v in (_kv_split(crumble) for crumble in crumbles[1:])}
        return cls(name=name, value=value, **attributes)


cookiejar_adapter = type_adapter.TypeAdapter(list[Cookie])
