"""LLM Python Code Sandbox Package.

A simple, isolated Python code execution environment for LLMs.
"""

from .core import (
    Sandbox,
    sandboxes,
    create_new_sandbox,
    get_sandbox,
    close_and_cleanup_sandbox,
    get_all_sandboxes_info,
    init_base_venv_image,
)
from .server import app, run_server
from .client import SandboxClient
from .client_mcp import MCPClient

__version__ = "0.2.1"
__all__ = [
    "Sandbox",
    "SandboxClient",
    "MCPClient",
    "sandboxes",
    "create_new_sandbox",
    "get_sandbox",
    "close_and_cleanup_sandbox",
    "get_all_sandboxes_info",
    "init_base_venv_image",
    "app",
    "run_server",
]
