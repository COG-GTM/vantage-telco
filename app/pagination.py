from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query

MAX_LIMIT = 500
DEFAULT_LIMIT = 50


@dataclass(frozen=True)
class Page:
    limit: int
    offset: int

    def envelope(self, items: Sequence[Any], **extra: Any) -> dict[str, Any]:
        return {
            "items": list(items[self.offset : self.offset + self.limit]),
            "total": len(items),
            "limit": self.limit,
            "offset": self.offset,
            **extra,
        }


def page_params(
    limit: int = Query(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(default=0, ge=0),
) -> Page:
    return Page(limit=limit, offset=offset)


PageDep = Annotated[Page, Depends(page_params)]
