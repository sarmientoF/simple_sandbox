"""E2B Code Interpreter compatible API.

This module provides a drop-in replacement for the e2b_code_interpreter package.
Users can use their existing E2B imports without any changes:

    from e2b_code_interpreter import Sandbox

    with Sandbox() as sandbox:
        execution = sandbox.run_code("x = 1 + 1; x")
        print(execution.text)  # "2"
"""

# Re-export everything from simple_sandbox
from simple_sandbox import (
    # E2B-compatible API (primary)
    Sandbox,
    AsyncSandbox,
    Execution,
    Result,
    Logs,
    ExecutionError,
    OutputMessage,
)

__all__ = [
    "Sandbox",
    "AsyncSandbox",
    "Execution",
    "Result",
    "Logs",
    "ExecutionError",
    "OutputMessage",
]
