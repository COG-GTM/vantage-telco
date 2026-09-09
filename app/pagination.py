from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from fastapi import Query

T = TypeVar("T")


class PageParams:
    def __init__(
        self,
        limit: int = Query(default=50, ge=1, le=500),  # noqa: B008
        offset: int = Query(default=0, ge=0),  # noqa: B008
    ):
        self.limit = limit
        self.offset = offset


def paginate(items: Sequence[T], limit: int, offset: int) -> tuple[list[T], dict[str, int | bool]]:
    page = list(items[offset : offset + limit])
    return page, {
        "limit": limit,
        "offset": offset,
        "total": len(items),
        "has_more": offset + len(page) < len(items),
    }
