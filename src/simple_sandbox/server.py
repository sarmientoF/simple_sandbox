"""FastAPI server for LLM Python Code Sandbox."""

import asyncio
import uvicorn
import os
from fastapi import FastAPI, UploadFile, Body, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi_mcp import FastApiMCP

from .core import (
    create_new_sandbox,
    get_sandbox,
    close_and_cleanup_sandbox,
    get_all_sandboxes_info,
    cleanup_expired_sandboxes,
    init_base_venv_image
)

# Create FastAPI application
app = FastAPI(title="LLM Python Code Sandbox")


@app.post("/sandbox/create", operation_id="create_sandbox")
async def create_sandbox():
    """
    Create a new Python code sandbox environment.

    **Response:**
    - `sandbox_id`: string, unique identifier for the new sandbox

    **Errors:**
    - 500: Failed to create sandbox
    """
    try:
        sandbox_id = create_new_sandbox()
        return {"sandbox_id": sandbox_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sandbox/{sandbox_id}/install", operation_id="install_package")
async def install_package(sandbox_id: str, package_name: str = Body(..., embed=True)):
    """
    Install a Python package in the specified sandbox.

    **Path Parameters:**
    - `sandbox_id`: string, sandbox unique identifier

    **Request Body:**
    - `package_name`: string, name of the Python package to install

    **Errors:**
    - 404: Sandbox not found
    - 500: Failed to install package
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    try:
        result = sandbox.install_package(package_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sandbox/{sandbox_id}/execute", operation_id="execute_code")
async def execute_code(sandbox_id: str, code: str = Body(..., embed=True)):
    """
    Execute Python code in the specified sandbox.

    **Path Parameters:**
    - `sandbox_id`: string, sandbox unique identifier

    **Request Body:**
    - `code`: string, Python code to execute

    **Response:**
    - Execution result including stdout, stderr, and status

    **Errors:**
    - 404: Sandbox not found
    - 500: Code execution failed
    """
    print(f"▶️ Received code to execute: {code[:100]}..." if len(code) > 100 else f"▶️ Received code to execute: {code}")
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    try:
        result = sandbox.execute_code(code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sandbox/{sandbox_id}/upload", operation_id="upload_file")
async def upload_file(sandbox_id: str, file: UploadFile = File(...), file_path: str = None):
    """
    Upload a file to the specified sandbox.

    **Path Parameters:**
    - `sandbox_id`: string, sandbox unique identifier

    **Form Parameters:**
    - `file`: file object to upload
    - `file_path`: string (optional), save path in sandbox

    **Response:**
    - `file_path`: string, full path of the saved file

    **Errors:**
    - 404: Sandbox not found
    - 500: File upload failed
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    try:
        saved_path = sandbox.upload_file(file, file_path)
        return {"file_path": saved_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sandbox/{sandbox_id}/files", operation_id="list_files")
async def list_files(sandbox_id: str):
    """
    Get the list of files in the specified sandbox.

    **Path Parameters:**
    - `sandbox_id`: string, sandbox unique identifier

    **Response:**
    - List of files with name, path, and size

    **Errors:**
    - 404: Sandbox not found
    - 500: Failed to get file list
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    try:
        return sandbox.get_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sandbox/{sandbox_id}/download/{file_path:path}", operation_id="download_file")
async def download_file(sandbox_id: str, file_path: str):
    """
    Download a file from the specified sandbox.

    **Path Parameters:**
    - `sandbox_id`: string, sandbox unique identifier
    - `file_path`: string, path of the file in the sandbox

    **Response:**
    - File content as download response

    **Errors:**
    - 404: Sandbox or file not found
    - 403: File access denied
    - 500: File download failed
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    try:
        full_path = sandbox.get_file_path(file_path)
        if not full_path:
            raise HTTPException(status_code=404, detail="File access denied")
        if not os.path.exists(full_path):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(full_path, filename=os.path.basename(file_path))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sandbox/{sandbox_id}/close", operation_id="close_sandbox")
async def close_sandbox(sandbox_id: str, background_tasks: BackgroundTasks):
    """
    Close and cleanup the specified sandbox.

    **Path Parameters:**
    - `sandbox_id`: string, sandbox unique identifier

    **Response:**
    - `status`: string, "success" on success
    - `message`: string, operation result description

    **Errors:**
    - 404: Sandbox not found
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    background_tasks.add_task(close_and_cleanup_sandbox, sandbox_id)

    return {"status": "success", "message": "Sandbox closed"}


@app.get("/sandboxes", operation_id="list_sandboxes")
async def list_sandboxes():
    """
    Get information about all active sandboxes (for debugging).

    **Response:**
    - List of sandbox information including ID and creation time
    """
    return get_all_sandboxes_info()


@app.get("/health")
async def health_check():
    """
    Check service health status.

    **Response:**
    - `status`: string, "healthy" when service is running normally
    """
    return {"status": "healthy"}


async def periodic_cleanup():
    """Periodically cleanup expired sandboxes."""
    while True:
        try:
            await cleanup_expired_sandboxes()
        except Exception as e:
            print(f"❌ Cleanup task failed: {e}")
        await asyncio.sleep(3600)


# Create and mount MCP server
mcp = FastApiMCP(app)
mcp.mount_http()


async def run_server_async(host: str = "0.0.0.0", port: int = 8000):
    """Run the server asynchronously."""
    print("🚀 Initializing base virtual environment image...")
    init_base_venv_image()

    cleanup_task = asyncio.create_task(periodic_cleanup())

    try:
        config = uvicorn.Config(
            app,
            host=host,
            port=port
        )
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        print("🛑 Server is stopping...")
    finally:
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            print("🧹 Periodic cleanup task cancelled")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the server."""
    try:
        asyncio.run(run_server_async(host, port))
    except KeyboardInterrupt:
        print("🛑 Server stopped")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="LLM Python Code Sandbox Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host address")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    args = parser.parse_args()
    run_server(args.host, args.port)
