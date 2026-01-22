"""Experiment results registry for querying and analyzing results."""

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator, Literal

from .config import RESULTS_DIR, TASKS_DIR


@dataclass
class NormalizedResult:
    """Normalized experiment result with computed fields."""
    run_id: str
    task: str
    agent: str
    model: str
    status: Literal["pass", "fail", "error", "timeout"]
    duration_sec: float
    language: str  # "none" if null
    constraints: list[str]  # [] if null
    error_message: str | None
    created_at: datetime
    
    @classmethod
    def from_dict(cls, row: dict) -> "NormalizedResult":
        language = row.get("language") or "none"
        constraints = row.get("constraints") or []
        
        created_at = cls._parse_timestamp(row.get("run_id", ""))
        
        return cls(
            run_id=row.get("run_id", ""),
            task=row.get("task", ""),
            agent=row.get("agent", ""),
            model=row.get("model", ""),
            status=row.get("status", "error"),
            duration_sec=row.get("duration_sec", 0.0),
            language=language,
            constraints=constraints,
            error_message=row.get("error_message"),
            created_at=created_at,
        )
    
    @staticmethod
    def _parse_timestamp(run_id: str) -> datetime:
        """Parse timestamp from run_id prefix (YYYYMMDD_HHMMSS_...)."""
        match = re.match(r"(\d{8})_(\d{6})_", run_id)
        if match:
            date_str, time_str = match.groups()
            try:
                return datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")
            except ValueError:
                pass
        return datetime.min
    
    def matches(
        self,
        task: str | None = None,
        agent: str | None = None,
        model: str | None = None,
        language: str | None = None,
        status: list[str] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        contains: str | None = None,
        run_id: str | None = None,
        has_constraints: bool | None = None,
    ) -> bool:
        """Check if this result matches the given filters."""
        if task and self.task != task:
            return False
        if agent and self.agent != agent:
            return False
        if model and self.model != model:
            return False
        if language and self.language.lower() != language.lower():
            return False
        if status and self.status not in status:
            return False
        if since and self.created_at < since:
            return False
        if until and self.created_at >= until:
            return False
        if run_id and self.run_id != run_id:
            return False
        if has_constraints is True and not self.constraints:
            return False
        if has_constraints is False and self.constraints:
            return False
        if contains:
            search_text = f"{self.task} {self.agent} {self.model} {self.error_message or ''}"
            if contains.lower() not in search_text.lower():
                return False
        return True
    
    def group_key(self, group_by: list[str]) -> tuple:
        """Get grouping key for this result."""
        key_parts = []
        for field in group_by:
            if field == "task":
                key_parts.append(self.task)
            elif field == "agent":
                key_parts.append(self.agent)
            elif field == "model":
                key_parts.append(self.model)
            elif field == "language":
                key_parts.append(self.language)
            elif field == "status":
                key_parts.append(self.status)
        return tuple(key_parts)
    
    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "task": self.task,
            "agent": self.agent,
            "model": self.model,
            "language": self.language,
            "constraints": self.constraints,
            "status": self.status,
            "duration_sec": self.duration_sec,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at != datetime.min else None,
        }


class ResultsRegistry:
    """Query interface for experiment results."""
    
    def __init__(self, results_file: Path | None = None):
        self.results_file = results_file or (RESULTS_DIR / "results.jsonl")
    
    def iter_results(self) -> Iterator[NormalizedResult]:
        """Stream all results from JSONL file."""
        if not self.results_file.exists():
            return
        
        with open(self.results_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    yield NormalizedResult.from_dict(row)
                except json.JSONDecodeError:
                    continue
    
    def filter(
        self,
        task: str | None = None,
        agent: str | None = None,
        model: str | None = None,
        language: str | None = None,
        status: list[str] | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
        contains: str | None = None,
        run_id: str | None = None,
        has_constraints: bool | None = None,
        limit: int | None = None,
        sort_by: str = "time",
        descending: bool = True,
    ) -> list[NormalizedResult]:
        """Filter and sort results."""
        results = [
            r for r in self.iter_results()
            if r.matches(
                task=task, agent=agent, model=model, language=language,
                status=status, since=since, until=until, contains=contains,
                run_id=run_id, has_constraints=has_constraints,
            )
        ]
        
        if sort_by == "time":
            results.sort(key=lambda r: r.created_at, reverse=descending)
        elif sort_by == "duration":
            results.sort(key=lambda r: r.duration_sec, reverse=descending)
        elif sort_by == "task":
            results.sort(key=lambda r: r.task, reverse=descending)
        elif sort_by == "agent":
            results.sort(key=lambda r: r.agent, reverse=descending)
        elif sort_by == "status":
            results.sort(key=lambda r: r.status, reverse=descending)
        
        if limit:
            results = results[:limit]
        
        return results
    
    def latest(
        self,
        group_by: list[str] | None = None,
        **filter_kwargs,
    ) -> list[NormalizedResult]:
        """Get the latest result for each group."""
        if group_by is None:
            group_by = ["task", "agent", "language"]
        
        results = self.filter(sort_by="time", descending=True, **filter_kwargs)
        
        seen: dict[tuple, NormalizedResult] = {}
        for r in results:
            key = r.group_key(group_by)
            if key not in seen:
                seen[key] = r
        
        return sorted(seen.values(), key=lambda r: r.created_at, reverse=True)
    
    def stats(
        self,
        by: list[str] | None = None,
        **filter_kwargs,
    ) -> list[dict]:
        """Compute aggregate statistics."""
        if by is None:
            by = ["agent"]
        
        results = self.filter(**filter_kwargs)
        
        groups: dict[tuple, list[NormalizedResult]] = {}
        for r in results:
            key = r.group_key(by)
            groups.setdefault(key, []).append(r)
        
        stats_list = []
        for key, group_results in sorted(groups.items()):
            total = len(group_results)
            passed = sum(1 for r in group_results if r.status == "pass")
            failed = sum(1 for r in group_results if r.status == "fail")
            errors = sum(1 for r in group_results if r.status == "error")
            timeouts = sum(1 for r in group_results if r.status == "timeout")
            
            durations = [r.duration_sec for r in group_results]
            avg_duration = sum(durations) / len(durations) if durations else 0
            
            pass_rate = passed / total if total > 0 else 0
            
            stat = {
                **{field: key[i] for i, field in enumerate(by)},
                "total": total,
                "pass": passed,
                "fail": failed,
                "error": errors,
                "timeout": timeouts,
                "pass_rate": round(pass_rate, 3),
                "avg_duration_sec": round(avg_duration, 2),
            }
            stats_list.append(stat)
        
        return stats_list
    
    def gaps(
        self,
        tasks: list[str] | None = None,
        agents: list[str] | None = None,
        languages: list[str] | None = None,
        from_config: bool = False,
    ) -> list[dict]:
        """Find task/agent/language combos that haven't been run."""
        if from_config:
            tasks = tasks or [d.name for d in TASKS_DIR.iterdir() if d.is_dir()]
        
        if not tasks or not agents or not languages:
            raise ValueError("Must specify tasks, agents, and languages (or use from_config)")
        
        expected = set()
        for t in tasks:
            for a in agents:
                for lang in languages:
                    expected.add((t, a, lang))
        
        seen = set()
        for r in self.iter_results():
            seen.add((r.task, r.agent, r.language))
        
        missing = expected - seen
        
        return [
            {"task": t, "agent": a, "language": lang}
            for t, a, lang in sorted(missing)
        ]
    
    def errors(self, **filter_kwargs) -> list[NormalizedResult]:
        """Get all error results."""
        return self.filter(status=["error"], **filter_kwargs)
