"""
soraya.support_modes — S(x) modes, frames, and the structured support object.

Per v0.4.1 patch P3: a support mode is not valid merely because it is helpful.
It must carry a FRAME, because "what mode" is insufficient without "in what
frame". The same mode (tiny_step) can be safe or unsafe depending on frame:

    DEEP + tiny_step + task_progress      = invalid (advances restricted action)
    DEEP + tiny_step + process_navigation = valid   (pause, save, route to reviewer)
"""
from __future__ import annotations

from dataclasses import dataclass

# Support modes (v0.4.1 §7).
SUPPORT_MODES = (
    "clarify", "triage", "tiny_step", "reset", "reflection",
    "momentum", "verify", "escalate", "refuse",
)

# Support frames (v0.4.1 P3). The frame disambiguates intent.
SUPPORT_FRAMES = (
    "task_progress",       # moving forward on the task directly
    "process_navigation",  # navigating the process required before action
    "stabilization",       # addressing overload before anything else
    "verification",        # completing required checks before proceeding
    "agency_return",       # returning decision ownership to the user
    "boundary_response",   # explaining why the system cannot proceed
)


@dataclass
class SupportMode:
    """A structured support selection: mode + frame + scope."""
    mode: str
    frame: str
    action_scope: str = "general"
    compatibility_status: str = "unchecked"  # unchecked|passed|failed|fallback_applied
