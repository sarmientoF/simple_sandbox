# LLM Python Code Sandbox 🚀
> Self-Hosting an E2B-like coding playground

| Logo                                       | Description   |
|--------------------------------------------|---------------|
| <img src="./asset/logo.png" width="500px"> | A Python code sandbox HTTP service crafted for LLMs, enabling isolated Python execution environments with code execution, file operations, and MCP integration. 🎛️
|


## 🌟 Awesome Features

1. **E2B-Compatible API** 🔄: Drop-in replacement for E2B's code-interpreter SDK - **zero code changes required!**
2. **Create Sandbox** 🆕: Spin up a Jupyter kernel and get a unique ID in a flash! ⚡
3. **Execute Code** 💻: Run code and receive stdout, stderr, errors, tracebacks, and images. Supports Multi-Round Code Execution! 🎨
4. **File Operations** 📁: Upload and download files seamlessly. 📤📥
5. **Sandbox Isolation** 🔒: Each sandbox has its own Python virtual environment and working directory. 🛡️
6. **Auto-Cleanup** 🧹: Sandboxes automatically close after 24 hours. 🚿
7. **MCP Support** 🤖: Integrated with FastAPI-MCP for AI model integration. 🤝
8. **UV Powered** ⚡: Uses [uv](https://github.com/astral-sh/uv) for lightning-fast package installation.

## 🚀 Getting Started

### Installation

```bash
# Using pip
pip install git+https://github.com/sarmientoF/simple_sandbox.git

# Using uv (recommended)
uv pip install git+https://github.com/sarmientoF/simple_sandbox.git

# With async support
pip install "simple-sandbox[async] @ git+https://github.com/sarmientoF/simple_sandbox.git"
```

### Start the Server

```bash
# Using CLI
sandbox-server --port 8000

# Using uv
uv run sandbox-server --port 8000
```

## 📦 E2B-Compatible API (Recommended)

The API is designed to be compatible with [E2B's code-interpreter](https://github.com/e2b-dev/code-interpreter). Migrate from E2B with minimal changes!

### Basic Usage

```python
from simple_sandbox import Sandbox

# Using context manager (recommended)
with Sandbox.create() as sandbox:
    execution = sandbox.run_code("x = 1 + 1; x")
    print(execution.text)  # "2"

# Or manual management
sandbox = Sandbox.create()
execution = sandbox.run_code("print('Hello!')")
print(execution.logs.stdout)  # ["Hello!\n"]
sandbox.kill()
```

### Execution Results

```python
from simple_sandbox import Sandbox

with Sandbox.create() as sandbox:
    execution = sandbox.run_code("""
import math
print("Pi is:", math.pi)
result = math.sqrt(16)
result
""")

    # Access results
    print(execution.text)           # "4.0" (main result)
    print(execution.logs.stdout)    # ["Pi is: 3.141592653589793\n"]
    print(execution.logs.stderr)    # []
    print(execution.error)          # None (or ExecutionError if failed)

    # Results can contain images, HTML, etc.
    for result in execution.results:
        if result.png:
            print("Got an image!")
        if result.html:
            print("Got HTML:", result.html)
```

### Error Handling

```python
from simple_sandbox import Sandbox

with Sandbox.create() as sandbox:
    execution = sandbox.run_code("1/0")

    if execution.error:
        print(f"Error: {execution.error.name}")      # "ZeroDivisionError"
        print(f"Message: {execution.error.value}")   # "division by zero"
        print(f"Traceback:\n{execution.error.traceback}")
```

### Streaming Callbacks

```python
from simple_sandbox import Sandbox, OutputMessage, Result, ExecutionError

def on_stdout(msg: OutputMessage):
    print(f"[stdout] {msg.line}")

def on_result(result: Result):
    print(f"[result] {result.text}")

with Sandbox.create() as sandbox:
    execution = sandbox.run_code(
        "print('line 1'); print('line 2'); 42",
        on_stdout=on_stdout,
        on_result=on_result
    )
```

### Async Support

```python
import asyncio
from simple_sandbox import AsyncSandbox

async def main():
    async with await AsyncSandbox.create() as sandbox:
        execution = await sandbox.run_code("x = 1 + 1; x")
        print(execution.text)  # "2"

asyncio.run(main())
```

### File Operations

```python
from simple_sandbox import Sandbox

with Sandbox.create() as sandbox:
    # Upload a file
    sandbox.upload_file("data.txt", b"Hello, World!")

    # Execute code that uses the file
    sandbox.run_code("""
with open('data.txt') as f:
    print(f.read())
""")

    # List files
    files = sandbox.list_files()
    print(files)  # [{'path': 'data.txt', 'size': 13}, ...]

    # Download a file
    content = sandbox.download_file("data.txt")
    print(content)  # b"Hello, World!"
```

### Install Packages

```python
from simple_sandbox import Sandbox

with Sandbox.create() as sandbox:
    # Install a package
    success = sandbox.install("pandas")

    if success:
        execution = sandbox.run_code("""
import pandas as pd
df = pd.DataFrame({'a': [1, 2, 3]})
print(df)
""")
```

## 🔄 Migrating from E2B

**Zero code changes required!** Keep your existing imports:

```python
# This works out of the box!
from e2b_code_interpreter import Sandbox

with Sandbox() as sandbox:
    execution = sandbox.run_code("x = 1 + 1; x")
    print(execution.text)
```

Or use the `simple_sandbox` import if you prefer:

```python
from simple_sandbox import Sandbox
```

**Key differences from E2B cloud:**
- No API key required (self-hosted)
- Server must be running locally (`sandbox-server --port 8000`)
- Pass `base_url` to `Sandbox.create()` if not using default `http://localhost:8000`

## 📱 Legacy SandboxClient

The original client is still available:

```python
from simple_sandbox import SandboxClient

client = SandboxClient(base_url='http://localhost:8000')
client.create_sandbox()
client.execute_code("print('Hello!')")
client.close_sandbox()
```

## 🔌 MCP Client

```python
import asyncio
from simple_sandbox import MCPClient

async def main():
    client = MCPClient(mcp_server_url="http://localhost:8000/mcp")
    tools = await client.list_tools()
    result = await client.call_tool("create_sandbox", {})
    print(result)

asyncio.run(main())
```

## 🛠️ API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/sandbox/create` | Create a new sandbox |
| POST | `/sandbox/{id}/execute` | Execute code in sandbox |
| POST | `/sandbox/{id}/install` | Install a Python package |
| POST | `/sandbox/{id}/upload` | Upload a file |
| GET | `/sandbox/{id}/files` | List files in sandbox |
| GET | `/sandbox/{id}/download/{path}` | Download a file |
| POST | `/sandbox/{id}/close` | Close and cleanup sandbox |
| GET | `/sandboxes` | List all active sandboxes |
| GET | `/health` | Health check |

## 📋 Requirements

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) (recommended)

## 📄 License

MIT License
