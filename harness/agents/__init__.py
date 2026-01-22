"""Agent adapters for different AI coding tools."""

from .base import AgentRunner
from .codex_cli import CodexCLIRunner
from .claude_code import ClaudeCodeRunner
from .amp import AmpRunner


def get_agent(name: str) -> AgentRunner:
    """Get an agent runner by name."""
    agents = {
        "codex": CodexCLIRunner(),
        "claude-code": ClaudeCodeRunner(),
        "amp": AmpRunner(),
    }
    
    if name not in agents:
        raise ValueError(f"Unknown agent: {name}. Available: {list(agents.keys())}")
    
    return agents[name]


__all__ = ["AgentRunner", "CodexCLIRunner", "ClaudeCodeRunner", "AmpRunner", "get_agent"]
