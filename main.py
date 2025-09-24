import asyncio
import uvicorn
import os
import asyncio
from typing import Dict, List
from fastapi import FastAPI, UploadFile, Body, File, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from fastapi_mcp import FastApiMCP
from core import (
    create_new_sandbox,
    get_sandbox,
    close_and_cleanup_sandbox,
    get_all_sandboxes_info,
    cleanup_expired_sandboxes,
    init_base_venv_image
)

# 创建FastAPI应用
app = FastAPI(title="LLM Python Code Sandbox")

# 创建沙箱
@app.post("/sandbox/create",operation_id="create_sandbox")
async def create_sandbox():
    """
    创建一个新的Python代码沙箱环境

    **响应：**
    - `sandbox_id`: 字符串，新创建的沙箱唯一标识符

    **错误：**
    - 500: 创建沙箱失败时返回
    """
    try:
        sandbox_id = create_new_sandbox()
        return {"sandbox_id": sandbox_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 安装Python包
@app.post("/sandbox/{sandbox_id}/install",operation_id="install_package")
async def install_package(sandbox_id: str, package_name: str = Body(..., embed=True)):
    """
    在指定沙箱中安装Python包

    **路径参数：**
    - `sandbox_id`: 字符串，沙箱唯一标识符

    **请求体参数：**
    - `package_name`: 字符串，要安装的Python包名称

    **响应：**
    - 安装结果信息

    **错误：**
    - 404: 找不到指定的沙箱时返回
    - 500: 安装包失败时返回
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    try:
        result = sandbox.install_package(package_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 执行代码
@app.post("/sandbox/{sandbox_id}/execute",operation_id="execute_code")
async def execute_code(sandbox_id: str, code: str = Body(..., embed=True)):
    """
    在指定沙箱中执行Python代码

    **路径参数：**
    - `sandbox_id`: 字符串，沙箱唯一标识符

    **请求体参数：**
    - `code`: 字符串，要执行的Python代码

    **响应：**
    - 代码执行结果，包含标准输出、标准错误和执行状态

    **错误：**
    - 404: 找不到指定的沙箱时返回
    - 500: 代码执行失败时返回
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    try:
        result = sandbox.execute_code(code)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 上传文件
@app.post("/sandbox/{sandbox_id}/upload",operation_id="upload_file")
async def upload_file(sandbox_id: str, file: UploadFile = File(...), file_path: str = None):
    """
    上传文件到指定沙箱中

    **路径参数：**
    - `sandbox_id`: 字符串，沙箱唯一标识符

    **表单参数：**
    - `file`: 文件，要上传的文件对象
    - `file_path`: 字符串（可选），文件在沙箱中的保存路径，不指定则使用原文件名

    **响应：**
    - `file_path`: 字符串，文件在沙箱中的完整路径

    **错误：**
    - 404: 找不到指定的沙箱时返回
    - 500: 文件上传失败时返回
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    try:
        saved_path = sandbox.upload_file(file, file_path)
        return {"file_path": saved_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 获取文件列表
@app.get("/sandbox/{sandbox_id}/files",operation_id="list_files")
async def list_files(sandbox_id: str):
    """
    获取指定沙箱中的文件列表

    **路径参数：**
    - `sandbox_id`: 字符串，沙箱唯一标识符

    **响应：**
    - 文件列表，包含文件名、路径、大小等信息

    **错误：**
    - 404: 找不到指定的沙箱时返回
    - 500: 获取文件列表失败时返回
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    try:
        return sandbox.get_files()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 下载文件
@app.get("/sandbox/{sandbox_id}/download/{file_path:path}",operation_id="download_file")
async def download_file(sandbox_id: str, file_path: str):
    """
    从指定沙箱中下载文件

    **路径参数：**
    - `sandbox_id`: 字符串，沙箱唯一标识符
    - `file_path`: 字符串，文件在沙箱中的路径

    **响应：**
    - 文件内容，作为文件下载响应

    **错误：**
    - 404: 找不到指定的沙箱或文件时返回
    - 404: 文件访问被拒绝时返回
    - 500: 文件下载失败时返回
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


# 关闭沙箱
@app.post("/sandbox/{sandbox_id}/close",operation_id="close_sandbox")
async def close_sandbox(sandbox_id: str, background_tasks: BackgroundTasks):
    """
    关闭并清理指定的沙箱环境

    **路径参数：**
    - `sandbox_id`: 字符串，沙箱唯一标识符

    **响应：**
    - `status`: 字符串，操作状态，成功时为"success"
    - `message`: 字符串，操作结果描述

    **错误：**
    - 404: 找不到指定的沙箱时返回
    """
    sandbox = get_sandbox(sandbox_id)
    if not sandbox:
        raise HTTPException(status_code=404, detail="Sandbox not found")

    # 从字典中移除，但在后台任务中关闭
    background_tasks.add_task(close_and_cleanup_sandbox, sandbox_id)

    return {"status": "success", "message": "Sandbox closed"}


# 获取所有沙箱列表（用于调试）
@app.get("/sandboxes",operation_id="list_sandboxes")
async def list_sandboxes():
    """
    获取当前所有活跃沙箱的信息（调试用）

    **响应：**
    - 沙箱信息列表，包含每个沙箱的ID、创建时间等信息
    """
    return get_all_sandboxes_info()


# 健康检查
@app.get("/health")
async def health_check():
    """
    检查服务健康状态

    **响应：**
    - `status`: 字符串，服务状态，正常时为"healthy"
    """
    return {"status": "healthy"}


# 启动定期清理任务
async def periodic_cleanup():
    while True:
        try:
            # 每小时执行一次清理
            await cleanup_expired_sandboxes()
        except Exception as e:
            print(f"清理任务执行失败: {e}")
        # 等待1小时
        await asyncio.sleep(3600)

# 创建并挂载MCP服务器 - 移到所有端点定义之后
mcp = FastApiMCP(app)
mcp.mount_http()


# 启动应用
async def run_server_async(host: str = "0.0.0.0", port: int = 8000):
    # 初始化基础虚拟环境镜像
    print("初始化基础虚拟环境镜像...")
    init_base_venv_image()
    
    # 创建定期清理任务
    cleanup_task = asyncio.create_task(periodic_cleanup())
    
    try:
        # 启动HTTP服务器
        config = uvicorn.Config(
            app,
            host=host,
            port=port
        )
        server = uvicorn.Server(config)
        await server.serve()
    except KeyboardInterrupt:
        print("服务器正在停止...")
    finally:
        # 取消清理任务
        cleanup_task.cancel()
        try:
            # 等待任务被取消
            await cleanup_task
        except asyncio.CancelledError:
            print("定期清理任务已取消")


# 启动应用
def run_server(host: str = "0.0.0.0", port: int = 8000):
    try:
        # 使用asyncio.run来运行异步函数，传入host和port参数
        asyncio.run(run_server_async(host, port))
    except KeyboardInterrupt:
        print("服务器已停止")


if __name__ == "__main__":
    import argparse
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="LLM Python Code Sandbox Server")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="服务器主机地址")
    parser.add_argument("--port", type=int, default=8000, help="服务器端口")
    # 解析命令行参数
    args = parser.parse_args()
    # 启动服务器
    run_server(args.host, args.port)
