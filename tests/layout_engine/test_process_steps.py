from __future__ import annotations

from packages.core import ProcessSlide
from packages.core.slides import ProcessStep
from packages.layout_engine import LayoutEngine, map_slots


def test_process_steps_emit_accent_number_badges() -> None:
    slide = ProcessSlide(
        id="p",
        index=0,
        title="实施流程",
        steps=[ProcessStep(title="调研"), ProcessStep(title="设计"), ProcessStep(title="上线")],
    )
    slots = map_slots(slide, LayoutEngine().select("process"))
    nums = [s for s in slots if s.name.endswith(".num")]
    assert [s.value for s in nums] == ["1", "2", "3"]
    assert all(s.color_role == "accent" for s in nums)
    # 序号与步骤正文是分开的两组槽,正文不再带 "1." 前缀
    titles = [s for s in slots if s.name.endswith(".title") and s.name.startswith("step_")]
    assert [s.value for s in titles] == ["调研", "设计", "上线"]
