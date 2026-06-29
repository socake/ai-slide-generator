from __future__ import annotations

import pytest
from pydantic import ValidationError

from packages.core import Rect


def test_rect_fields() -> None:
    r = Rect(left=0.1, top=0.2, width=0.3, height=0.4)
    assert (r.left, r.top, r.width, r.height) == (0.1, 0.2, 0.3, 0.4)


def test_rect_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        Rect(left=-0.1, top=0.0, width=0.5, height=0.5)
    with pytest.raises(ValidationError):
        Rect(left=0.0, top=0.0, width=1.5, height=0.5)
