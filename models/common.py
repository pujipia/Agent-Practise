from typing import Literal

FlowDirection = Literal["TD", "LR", "RL", "BT"]
FlowNodeKind = Literal[
    "start_end",
    "process",
    "decision",
    "input_output",
    "subroutine",
]