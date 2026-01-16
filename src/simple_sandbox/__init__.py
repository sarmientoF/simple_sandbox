"""LLM Python Code Sandbox Package.

A simple, isolated Python code execution environment for LLMs.
E2B-compatible API for easy migration.
"""

# Core server components (internal)
from .core import (
    Sandbox as CoreSandbox,
    sandboxes,
    create_new_sandbox,
    get_sandbox,
    close_and_cleanup_sandbox,
    get_all_sandboxes_info,
    init_base_venv_image,
)
from .server import app, run_server

# E2B-compatible client API
from .sandbox import Sandbox
from .sandbox_async import AsyncSandbox
from .models import (
    Execution,
    Result,
    Logs,
    ExecutionError,
    OutputMessage,
)

# Legacy clients
from .client import SandboxClient
from .client_mcp import MCPClient

__version__ = "0.3.1"
__all__ = [
    # E2B-compatible API (primary)
    "Sandbox",
    "AsyncSandbox",
    "Execution",
    "Result",
    "Logs",
    "ExecutionError",
    "OutputMessage",
    # Legacy clients
    "SandboxClient",
    "MCPClient",
    # Server components
    "app",
    "run_server",
    # Core internals (for advanced usage)
    "CoreSandbox",
    "sandboxes",
    "create_new_sandbox",
    "get_sandbox",
    "close_and_cleanup_sandbox",
    "get_all_sandboxes_info",
    "init_base_venv_image",
]
