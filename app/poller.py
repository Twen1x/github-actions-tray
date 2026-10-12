from __future__ import annotations

import logging
from datetime import datetime, timezone

import requests

from app.action_state import ActionState
from app.config import AppConfig

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15

PER_PAGE = 1

def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        dt = datetime.fromisoformat(text)
    except (ValueError, TypeError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt

def _github_message(resp) -> str:
    try:
        data = resp.json()
    except ValueError:
        return ""
    if not isinstance(data, dict):
        return ""
    message = data.get("message")
    if not isinstance(message, str):
        return ""
    return message.strip()[:200]


class Poller:

    def __init__(self, cfg: AppConfig, states: list[ActionState]) -> None:
        self.cfg = cfg
        self.states = states
        self._logged_errors: dict[str, str] = {}

    def _api_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.cfg.github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    def fetch_state(self, st: ActionState) -> None:
        cfg = st.cfg
        url = (
            f"https://api.github.com/repos/{cfg.owner}/{cfg.repo}"
            f"/actions/workflows/{cfg.file}/runs"
        )
        params = {"branch": cfg.branch, "per_page": PER_PAGE}
        try:
            resp = requests.get(
                url,
                headers=self._api_headers(),
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 401:
                st.error = "401 (токен/сбой API)"
                st.fail_streak += 1
                self._log_api_error(st, resp)
                return
            if resp.status_code == 404:
                st.error = "404 (репо/workflow?)"
                st.fail_streak += 1
                self._log_api_error(st, resp)
                return
            resp.raise_for_status()
            runs = resp.json().get("workflow_runs", [])
            if not runs:
                st.status = None
                st.conclusion = None
                st.html_url = None
                st.head_sha = None
                st.last_commit_time = None
                st.author = None
                st.commit_message = None
                st.error = None
                st.has_data = True
                st.fail_streak = 0
                self._logged_errors.pop(st.label, None)
                return
            run = runs[0]
            head_commit = run.get("head_commit") or {}
            st.status = run.get("status")
            st.conclusion = run.get("conclusion")
            st.html_url = run.get("html_url")
            st.head_sha = run.get("head_sha") or head_commit.get("id")
            st.last_commit_time = _parse_datetime(
                head_commit.get("timestamp") or run.get("created_at")
            )
            author = head_commit.get("author") or {}
            st.author = (
                author.get("name")
                or author.get("email")
                or (run.get("triggering_actor") or {}).get("login")
                or (run.get("actor") or {}).get("login")
            )
            message = head_commit.get("message")
            st.commit_message = message.splitlines()[0] if message else None
            st.error = None
            st.has_data = True
            st.fail_streak = 0
            self._logged_errors.pop(st.label, None)
        except requests.RequestException as exc:
            st.error = str(exc)[:40]
            st.fail_streak += 1
            self._log_api_error(st, getattr(exc, "response", None))

    def _log_api_error(self, st: ActionState, resp) -> None:
        cfg = st.cfg
        message = _github_message(resp) if resp is not None else ""
        text = st.error or "ошибка запроса"
        if message:
            text = f"{text}: {message}"
        text = (
            f"{text} — {cfg.owner}/{cfg.repo} {cfg.file}@{cfg.branch}"
        )
        if self._logged_errors.get(st.label) == text:
            return
        self._logged_errors[st.label] = text
        logger.error("%s: %s", st.label, text)

    def check(self, cfg: AppConfig) -> list[tuple[bool, str]]:
        from app.tray import human_status

        states = [ActionState(label=a.label, cfg=a) for a in cfg.actions]
        saved_cfg = self.cfg
        saved_states = self.states
        saved_logged = self._logged_errors
        self.cfg = cfg
        self.states = states
        self._logged_errors = {}
        logged: dict[str, str] = {}
        try:
            self.poll_once()
            logged = dict(self._logged_errors)
        finally:
            self.cfg = saved_cfg
            self.states = saved_states
            self._logged_errors = saved_logged

        lines: list[tuple[bool, str]] = []
        for st in states:
            if st.error:
                detail = logged.get(st.label) or st.error
                lines.append((False, f"{st.label}: {detail}"))
            else:
                lines.append((True, f"{st.label}: {human_status(st, cfg.language)}"))
        return lines

    def poll_once(self) -> None:
        for st in self.states:
            self.fetch_state(st)

    def reconfigure(self, cfg: AppConfig) -> None:
        self.cfg = cfg
