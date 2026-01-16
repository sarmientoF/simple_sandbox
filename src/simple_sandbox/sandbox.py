"""E2B-compatible Sandbox class for code execution."""

from typing import Optional, Dict, Callable, Any, Union
import requests
import time

from .models import Execution, Result, Logs, ExecutionError, OutputMessage


# Type alias for output handlers
OutputHandler = Callable[[Any], Any]


class Sandbox:
    """
    E2B-compatible Sandbox class for executing code in isolated environments.

    Usage:
        # Using context manager (recommended)
        with Sandbox.create() as sandbox:
            execution = sandbox.run_code("x = 1 + 1; x")
            print(execution.text)  # "2"

        # Manual management
        sandbox = Sandbox.create()
        execution = sandbox.run_code("print('hello')")
        sandbox.kill()
    """

    def __init__(
        self,
        sandbox_id: str,
        base_url: str = "http://localhost:8000"
    ):
        """Initialize sandbox with an existing sandbox ID."""
        self.sandbox_id = sandbox_id
        self.base_url = base_url
        self._closed = False

    @classmethod
    def create(
        cls,
        base_url: str = "http://localhost:8000",
        timeout: Optional[float] = 300,
        **kwargs
    ) -> "Sandbox":
        """
        Create a new sandbox instance.

        Args:
            base_url: URL of the sandbox server
            timeout: Execution timeout in seconds (default: 300)
            **kwargs: Additional arguments (ignored for compatibility)

        Returns:
            A new Sandbox instance
        """
        response = requests.post(
            f"{base_url}/sandbox/create",
            timeout=timeout
        )
        if response.status_code != 200:
            raise RuntimeError(f"Failed to create sandbox: {response.text}")

        sandbox_id = response.json()["sandbox_id"]
        return cls(sandbox_id, base_url)

    def run_code(
        self,
        code: str,
        language: Optional[str] = None,
        on_stdout: Optional[OutputHandler] = None,
        on_stderr: Optional[OutputHandler] = None,
        on_result: Optional[OutputHandler] = None,
        on_error: Optional[OutputHandler] = None,
        envs: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        request_timeout: Optional[float] = 60,
        **kwargs
    ) -> Execution:
        """
        Execute code in the sandbox.

        Args:
            code: The code to execute
            language: Programming language (ignored, always Python)
            on_stdout: Callback for stdout messages
            on_stderr: Callback for stderr messages
            on_result: Callback for results
            on_error: Callback for errors
            envs: Environment variables (not yet supported)
            timeout: Execution timeout in seconds
            request_timeout: HTTP request timeout in seconds
            **kwargs: Additional arguments (ignored for compatibility)

        Returns:
            Execution object with results, logs, and error info
        """
        if self._closed:
            raise RuntimeError("Sandbox is closed")

        response = requests.post(
            f"{self.base_url}/sandbox/{self.sandbox_id}/execute",
            json={"code": code},
            timeout=request_timeout
        )

        if response.status_code == 404:
            raise RuntimeError("Sandbox not found")
        if response.status_code != 200:
            raise RuntimeError(f"Failed to execute code: {response.text}")

        data = response.json()

        # Parse results
        results = []
        for item in data.get("results", []):
            result = Result(
                text=item.get("data") if item.get("type") == "text/plain" else None,
                html=item.get("data") if item.get("type") == "text/html" else None,
                png=item.get("data") if item.get("type") == "image/png" else None,
                jpeg=item.get("data") if item.get("type") == "image/jpeg" else None,
                svg=item.get("data") if item.get("type") == "image/svg+xml" else None,
                is_main_result=True
            )
            results.append(result)
            if on_result:
                on_result(result)

        # Parse logs
        stdout_lines = data.get("stdout", [])
        stderr_lines = data.get("stderr", [])
        logs = Logs(stdout=stdout_lines, stderr=stderr_lines)

        # Call stdout/stderr handlers
        if on_stdout:
            for line in stdout_lines:
                on_stdout(OutputMessage(line=line, timestamp=int(time.time() * 1e9)))
        if on_stderr:
            for line in stderr_lines:
                on_stderr(OutputMessage(line=line, timestamp=int(time.time() * 1e9), error=True))

        # Parse error
        error = None
        error_data = data.get("error")
        if error_data:
            error = ExecutionError(
                name=error_data.get("name", "Error"),
                value=error_data.get("value", ""),
                traceback="\n".join(error_data.get("traceback", []))
            )
            if on_error:
                on_error(error)

        return Execution(
            results=results,
            logs=logs,
            error=error
        )

    def install(self, package: str, timeout: Optional[float] = 120) -> bool:
        """
        Install a Python package in the sandbox.

        Args:
            package: Package name to install
            timeout: Installation timeout in seconds

        Returns:
            True if installation succeeded
        """
        if self._closed:
            raise RuntimeError("Sandbox is closed")

        response = requests.post(
            f"{self.base_url}/sandbox/{self.sandbox_id}/install",
            json={"package_name": package},
            timeout=timeout
        )

        if response.status_code != 200:
            return False

        return response.json().get("success", False)

    def upload_file(
        self,
        file_path: str,
        content: bytes,
        timeout: Optional[float] = 60
    ) -> str:
        """
        Upload a file to the sandbox.

        Args:
            file_path: Destination path in sandbox
            content: File content as bytes
            timeout: Upload timeout in seconds

        Returns:
            Path of uploaded file
        """
        if self._closed:
            raise RuntimeError("Sandbox is closed")

        files = {"file": (file_path, content)}
        response = requests.post(
            f"{self.base_url}/sandbox/{self.sandbox_id}/upload",
            files=files,
            timeout=timeout
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to upload file: {response.text}")

        return response.json().get("file_path", file_path)

    def download_file(
        self,
        file_path: str,
        timeout: Optional[float] = 60
    ) -> bytes:
        """
        Download a file from the sandbox.

        Args:
            file_path: Path of file in sandbox
            timeout: Download timeout in seconds

        Returns:
            File content as bytes
        """
        if self._closed:
            raise RuntimeError("Sandbox is closed")

        response = requests.get(
            f"{self.base_url}/sandbox/{self.sandbox_id}/download/{file_path}",
            timeout=timeout
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to download file: {response.text}")

        return response.content

    def list_files(self, timeout: Optional[float] = 30) -> list:
        """
        List files in the sandbox.

        Returns:
            List of file info dicts with 'path' and 'size' keys
        """
        if self._closed:
            raise RuntimeError("Sandbox is closed")

        response = requests.get(
            f"{self.base_url}/sandbox/{self.sandbox_id}/files",
            timeout=timeout
        )

        if response.status_code != 200:
            raise RuntimeError(f"Failed to list files: {response.text}")

        return response.json()

    def kill(self, timeout: Optional[float] = 30) -> None:
        """Close and cleanup the sandbox."""
        if self._closed:
            return

        try:
            requests.post(
                f"{self.base_url}/sandbox/{self.sandbox_id}/close",
                timeout=timeout
            )
        except Exception:
            pass
        finally:
            self._closed = True

    def close(self) -> None:
        """Alias for kill()."""
        self.kill()

    @property
    def is_running(self) -> bool:
        """Check if sandbox is still running."""
        return not self._closed

    def __enter__(self) -> "Sandbox":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - automatically close sandbox."""
        self.kill()

    def __del__(self):
        """Destructor - attempt to close sandbox."""
        try:
            self.kill()
        except Exception:
            pass
