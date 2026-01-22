"""CLI for querying experiment results."""

import argparse
import json
import sys
from datetime import datetime, timedelta

from .registry import ResultsRegistry


def parse_date(s: str) -> datetime:
    """Parse date string (ISO format or relative like '1d', '2w')."""
    if s.endswith("d"):
        days = int(s[:-1])
        return datetime.now() - timedelta(days=days)
    if s.endswith("w"):
        weeks = int(s[:-1])
        return datetime.now() - timedelta(weeks=weeks)
    return datetime.fromisoformat(s)


def format_table(rows: list[dict], columns: list[str]) -> str:
    """Format rows as a simple table."""
    if not rows:
        return "(no results)"
    
    widths = {col: len(col) for col in columns}
    for row in rows:
        for col in columns:
            val = str(row.get(col, ""))
            widths[col] = max(widths[col], min(len(val), 60))
    
    header = " | ".join(col.ljust(widths[col]) for col in columns)
    separator = "-+-".join("-" * widths[col] for col in columns)
    
    lines = [header, separator]
    for row in rows:
        line = " | ".join(
            str(row.get(col, ""))[:60].ljust(widths[col])
            for col in columns
        )
        lines.append(line)
    
    return "\n".join(lines)


def output(data: list[dict], fmt: str, columns: list[str] | None = None):
    """Output data in the requested format."""
    if fmt == "json":
        print(json.dumps(data, indent=2, default=str))
    elif fmt == "jsonl":
        for row in data:
            print(json.dumps(row, default=str))
    elif fmt == "csv":
        if not data:
            return
        cols = columns or list(data[0].keys())
        print(",".join(cols))
        for row in data:
            print(",".join(str(row.get(c, "")) for c in cols))
    else:  # table
        cols = columns or list(data[0].keys()) if data else []
        print(format_table(data, cols))


def add_common_args(parser: argparse.ArgumentParser):
    """Add common filter arguments to a subparser."""
    parser.add_argument("--task", help="Filter by task name")
    parser.add_argument("--agent", help="Filter by agent")
    parser.add_argument("--model", help="Filter by model")
    parser.add_argument("--language", help="Filter by language (use 'none' for null)")
    parser.add_argument("--status", action="append", help="Filter by status (repeatable)")
    parser.add_argument("--since", help="Filter results after date (ISO or '1d', '2w')")
    parser.add_argument("--until", help="Filter results before date")
    parser.add_argument("--contains", help="Text search in task/agent/error")
    parser.add_argument("--run-id", help="Filter by specific run ID")
    parser.add_argument("--has-constraints", action="store_true", default=None,
                        help="Only results with constraints")
    parser.add_argument("--no-constraints", action="store_true",
                        help="Only results without constraints")
    parser.add_argument("--limit", type=int, help="Limit number of results")
    parser.add_argument("--format", choices=["table", "json", "jsonl", "csv"],
                        default="table", help="Output format")


def get_filter_kwargs(args) -> dict:
    """Extract filter kwargs from parsed args."""
    kwargs = {}
    if args.task:
        kwargs["task"] = args.task
    if args.agent:
        kwargs["agent"] = args.agent
    if args.model:
        kwargs["model"] = args.model
    if args.language:
        kwargs["language"] = args.language
    if args.status:
        kwargs["status"] = args.status
    if args.since:
        kwargs["since"] = parse_date(args.since)
    if args.until:
        kwargs["until"] = parse_date(args.until)
    if args.contains:
        kwargs["contains"] = args.contains
    if args.run_id:
        kwargs["run_id"] = args.run_id
    if args.has_constraints:
        kwargs["has_constraints"] = True
    elif getattr(args, "no_constraints", False):
        kwargs["has_constraints"] = False
    if args.limit:
        kwargs["limit"] = args.limit
    return kwargs


def cmd_list(args):
    """List matching results."""
    registry = ResultsRegistry()
    kwargs = get_filter_kwargs(args)
    results = registry.filter(**kwargs)
    
    data = [r.to_dict() for r in results]
    columns = ["created_at", "task", "agent", "language", "status", "duration_sec"]
    if args.format == "table":
        for d in data:
            if d["created_at"]:
                d["created_at"] = d["created_at"][:16]  # Truncate for display
            d["duration_sec"] = f"{d['duration_sec']:.1f}s"
    output(data, args.format, columns)


def cmd_latest(args):
    """Show latest result per group."""
    registry = ResultsRegistry()
    kwargs = get_filter_kwargs(args)
    
    group_by = args.group_by.split(",") if args.group_by else ["task", "agent", "language"]
    results = registry.latest(group_by=group_by, **kwargs)
    
    data = [r.to_dict() for r in results]
    columns = group_by + ["status", "duration_sec", "created_at"]
    if args.format == "table":
        for d in data:
            if d["created_at"]:
                d["created_at"] = d["created_at"][:16]
            d["duration_sec"] = f"{d['duration_sec']:.1f}s"
    output(data, args.format, columns)


def cmd_errors(args):
    """Show error results."""
    registry = ResultsRegistry()
    kwargs = get_filter_kwargs(args)
    results = registry.errors(**kwargs)
    
    data = [r.to_dict() for r in results]
    columns = ["created_at", "task", "agent", "language", "error_message"]
    if args.format == "table":
        for d in data:
            if d["created_at"]:
                d["created_at"] = d["created_at"][:16]
            if d["error_message"] and len(d["error_message"]) > 50:
                d["error_message"] = d["error_message"][:47] + "..."
    output(data, args.format, columns)


def cmd_stats(args):
    """Show aggregate statistics."""
    registry = ResultsRegistry()
    kwargs = get_filter_kwargs(args)
    
    by = args.by.split(",") if args.by else ["agent"]
    data = registry.stats(by=by, **kwargs)
    
    columns = by + ["total", "pass", "fail", "error", "timeout", "pass_rate", "avg_duration_sec"]
    if args.format == "table":
        for d in data:
            d["pass_rate"] = f"{d['pass_rate'] * 100:.1f}%"
            d["avg_duration_sec"] = f"{d['avg_duration_sec']:.1f}s"
    output(data, args.format, columns)


def cmd_gaps(args):
    """Show missing task/agent/language combos."""
    registry = ResultsRegistry()
    
    tasks = args.tasks.split(",") if args.tasks else None
    agents = args.agents.split(",") if args.agents else None
    languages = args.languages.split(",") if args.languages else None
    
    try:
        data = registry.gaps(
            tasks=tasks,
            agents=agents,
            languages=languages,
            from_config=args.from_config,
        )
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    columns = ["task", "agent", "language"]
    output(data, args.format, columns)
    
    if args.format == "table":
        print(f"\n{len(data)} missing combinations")


def cmd_show(args):
    """Show details for a specific run."""
    registry = ResultsRegistry()
    results = registry.filter(run_id=args.run_id)
    
    if not results:
        print(f"No result found for run_id: {args.run_id}", file=sys.stderr)
        sys.exit(1)
    
    data = results[0].to_dict()
    if args.format == "json":
        print(json.dumps(data, indent=2, default=str))
    else:
        for key, val in data.items():
            print(f"{key}: {val}")


def main():
    parser = argparse.ArgumentParser(
        prog="speedway-results",
        description="Query and analyze LLM Speedway experiment results"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # list
    p_list = subparsers.add_parser("list", help="List matching results")
    add_common_args(p_list)
    p_list.set_defaults(func=cmd_list)
    
    # latest
    p_latest = subparsers.add_parser("latest", help="Show latest result per group")
    add_common_args(p_latest)
    p_latest.add_argument("--group-by", default="task,agent,language",
                          help="Comma-separated grouping fields")
    p_latest.set_defaults(func=cmd_latest)
    
    # errors
    p_errors = subparsers.add_parser("errors", help="Show error results")
    add_common_args(p_errors)
    p_errors.set_defaults(func=cmd_errors)
    
    # stats
    p_stats = subparsers.add_parser("stats", help="Show aggregate statistics")
    add_common_args(p_stats)
    p_stats.add_argument("--by", default="agent",
                         help="Comma-separated grouping fields")
    p_stats.set_defaults(func=cmd_stats)
    
    # gaps
    p_gaps = subparsers.add_parser("gaps", help="Show missing combinations")
    p_gaps.add_argument("--tasks", help="Comma-separated task names")
    p_gaps.add_argument("--agents", help="Comma-separated agent names")
    p_gaps.add_argument("--languages", help="Comma-separated languages")
    p_gaps.add_argument("--from-config", action="store_true",
                        help="Load tasks from config directory")
    p_gaps.add_argument("--format", choices=["table", "json", "jsonl", "csv"],
                        default="table")
    p_gaps.set_defaults(func=cmd_gaps)
    
    # show
    p_show = subparsers.add_parser("show", help="Show details for a run")
    p_show.add_argument("run_id", help="Run ID to show")
    p_show.add_argument("--format", choices=["table", "json"], default="table")
    p_show.set_defaults(func=cmd_show)
    
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
