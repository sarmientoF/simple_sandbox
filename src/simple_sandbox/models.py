"""E2B-compatible data models for code execution results."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Iterable
import json


@dataclass
class ExecutionError:
    """Represents an error during code execution."""
    name: str
    value: str
    traceback: str

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "name": self.name,
            "value": self.value,
            "traceback": self.traceback
        })

    def __str__(self) -> str:
        return f"{self.name}: {self.value}"


@dataclass
class Logs:
    """Contains captured stdout and stderr output."""
    stdout: List[str] = field(default_factory=list)
    stderr: List[str] = field(default_factory=list)

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "stdout": self.stdout,
            "stderr": self.stderr
        })


@dataclass
class Result:
    """Represents individual result data from execution."""
    text: Optional[str] = None
    html: Optional[str] = None
    markdown: Optional[str] = None
    svg: Optional[str] = None
    png: Optional[str] = None
    jpeg: Optional[str] = None
    pdf: Optional[str] = None
    latex: Optional[str] = None
    json_data: Optional[Dict[str, Any]] = None
    javascript: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    is_main_result: bool = False
    extra: Optional[Dict[str, Any]] = None

    def formats(self) -> Iterable[str]:
        """Get available format types."""
        formats = []
        if self.text is not None:
            formats.append("text/plain")
        if self.html is not None:
            formats.append("text/html")
        if self.markdown is not None:
            formats.append("text/markdown")
        if self.svg is not None:
            formats.append("image/svg+xml")
        if self.png is not None:
            formats.append("image/png")
        if self.jpeg is not None:
            formats.append("image/jpeg")
        if self.pdf is not None:
            formats.append("application/pdf")
        if self.latex is not None:
            formats.append("text/latex")
        if self.json_data is not None:
            formats.append("application/json")
        if self.javascript is not None:
            formats.append("application/javascript")
        return formats

    def __getitem__(self, key: str) -> Any:
        """Dict-like access to result data."""
        return getattr(self, key, None)

    def __str__(self) -> str:
        if self.text:
            return self.text
        return repr(self)

    # Jupyter display protocol methods
    def _repr_html_(self) -> Optional[str]:
        return self.html

    def _repr_markdown_(self) -> Optional[str]:
        return self.markdown

    def _repr_svg_(self) -> Optional[str]:
        return self.svg

    def _repr_png_(self) -> Optional[str]:
        return self.png

    def _repr_jpeg_(self) -> Optional[str]:
        return self.jpeg

    def _repr_pdf_(self) -> Optional[str]:
        return self.pdf

    def _repr_latex_(self) -> Optional[str]:
        return self.latex

    def _repr_json_(self) -> Optional[Dict[str, Any]]:
        return self.json_data

    def _repr_javascript_(self) -> Optional[str]:
        return self.javascript


@dataclass
class Execution:
    """Represents the result of code execution."""
    results: List[Result] = field(default_factory=list)
    logs: Logs = field(default_factory=Logs)
    error: Optional[ExecutionError] = None
    execution_count: Optional[int] = None

    @property
    def text(self) -> Optional[str]:
        """Text representation of the main result."""
        for result in self.results:
            if result.is_main_result and result.text:
                return result.text
        # Fall back to first result with text
        for result in self.results:
            if result.text:
                return result.text
        # Fall back to stdout
        if self.logs.stdout:
            return "".join(self.logs.stdout)
        return None

    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "results": [
                {k: v for k, v in r.__dict__.items() if v is not None}
                for r in self.results
            ],
            "logs": {
                "stdout": self.logs.stdout,
                "stderr": self.logs.stderr
            },
            "error": {
                "name": self.error.name,
                "value": self.error.value,
                "traceback": self.error.traceback
            } if self.error else None,
            "execution_count": self.execution_count
        })


@dataclass
class OutputMessage:
    """Represents a single line of output during streaming."""
    line: str
    timestamp: int = 0
    error: bool = False
