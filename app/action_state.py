from __future__ import annotations

from datetime import datetime

from app.config import ActionConfig

Color = tuple[int, int, int]

COLOR_RUNNING: Color = (227, 179, 65)
COLOR_RUNNING_DIM: Color = (120, 96, 35)
COLOR_SUCCESS: Color = (45, 164, 78)
COLOR_FAILURE: Color = (203, 36, 49)
COLOR_UNKNOWN: Color = (110, 118, 129)
COLOR_LOADING: Color = (47, 129, 247)

RUNNING_STATUSES = {"queued", "in_progress", "requested", "waiting", "pending"}

FAILURE_CONCLUSIONS = {"failure", "timed_out", "startup_failure"}

NO_SHA = "--"

class ActionState:

    label: str
    cfg: ActionConfig
    status: str | None
    conclusion: str | None
    head_sha: str | None
    last_commit_time: datetime | None
    html_url: str | None
    error: str | None
    has_data: bool
    fail_streak: int

    def __init__(
        self,
        label: str,
        cfg: ActionConfig,
        status: str | None = None,
        conclusion: str | None = None,
        head_sha: str | None = None,
        last_commit_time: datetime | None = None,
        html_url: str | None = None,
        error: str | None = None,
        has_data: bool = False,
        fail_streak: int = 0,
        author: str | None = None,
        commit_message: str | None = None,
    ) -> None:
        self.label = label
        self.cfg = cfg
        self.status = status
        self.conclusion = conclusion
        self.head_sha = head_sha
        self.last_commit_time = last_commit_time
        self.html_url = html_url
        self.error = error
        self.has_data = has_data
        self.fail_streak = fail_streak
        self.author = author
        self.commit_message = commit_message

    @property
    def is_running(self) -> bool:
        return self.status in RUNNING_STATUSES

    @property
    def is_loading(self) -> bool:
        return not self.has_data and not self.error

    def color(self) -> Color:
        if not self.has_data:
            return COLOR_UNKNOWN if self.error else COLOR_LOADING
        if self.is_running:
            return COLOR_RUNNING
        if self.status == "completed":
            if self.conclusion == "success":
                return COLOR_SUCCESS
            if self.conclusion in FAILURE_CONCLUSIONS:
                return COLOR_FAILURE
            return COLOR_UNKNOWN
        return COLOR_UNKNOWN

    def short_sha(self) -> str:
        if self.head_sha:
            return self.head_sha[:7]
        return NO_SHA

    def author_text(self) -> str:
        return self.author if self.author else NO_SHA

    def message_text(self) -> str:
        if not self.commit_message:
            return NO_SHA
        return self.commit_message.splitlines()[0] if self.commit_message else NO_SHA
