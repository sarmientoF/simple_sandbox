import os
import uuid
import asyncio
import shutil
import subprocess
from typing import Dict, Optional, List
from fastapi import UploadFile, HTTPException
from jupyter_client import KernelManager
import tempfile
import venv
import re

# 用于过滤jupyter打印日志中的颜色等特殊字符
ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

# 存储所有沙箱实例
sandboxes: Dict[str, Dict] = {}

# 基础虚拟环境镜像路径
BASE_VENV_IMAGE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "base_venv_image")

# 常用数据分析包列表
COMMON_PACKAGES = ['ipykernel', 'numpy', 'pandas', 'matplotlib', 'scipy', 'seaborn']

# 绘图中文字体支持
font_code = """import os
import matplotlib as mpl
import matplotlib.font_manager as fm

# 1. 注册自定义字体
font_path = os.path.join(os.getcwd(), 'SimHei.ttf')  # 拼接字体文件完整路径
fm.fontManager.addfont(font_path)

# 2. 把微软雅黑字体添加到serif字体中
font_name = fm.FontProperties(fname=font_path).get_name()  # 获取字体名称
mpl.rcParams['font.sans-serif'] = [font_name] + mpl.rcParams['font.sans-serif']  # 插入到字体列表首位
mpl.rcParams['font.family'] = 'sans-serif'  # 应用字体族
"""


# 沙箱类
class Sandbox:
    def __init__(self, sandbox_id: str, work_dir: str, venv_dir: str):
        self.sandbox_id = sandbox_id
        self.work_dir = work_dir
        self.venv_dir = venv_dir

        # 配置KernelManager使用虚拟环境中的Python解释器
        self.kernel_manager = KernelManager(
            kernel_name='python3',
            kernel_spec_manager=self._create_custom_kernel_spec_manager()
        )
        # 设置环境变量
        env = os.environ.copy()
        env['VIRTUAL_ENV'] = venv_dir

        # 设置内核使用虚拟环境中的Python
        self.kernel_manager.start_kernel(
            cwd=work_dir,
            env=env,
        )

        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        self.kernel_client.wait_for_ready()
        self.last_execute_id = 0

        # 复制字体文件到沙箱工作目录
        font_source_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'SimHei.ttf')
        font_dest_path = os.path.join(work_dir, 'SimHei.ttf')
        if os.path.exists(font_source_path):
            try:
                shutil.copy2(font_source_path, font_dest_path)
                print(f"字体文件已复制到: {font_dest_path}")
            except Exception as e:
                print(f"复制字体文件失败: {e}")
        else:
            print(f"未找到字体文件: {font_source_path}")

        # 安装基本包
        self._install_basic_packages()
        
        # 执行字体注册代码
        self.execute_code(font_code)

    def _create_custom_kernel_spec_manager(self):
        # 创建自定义的内核规范管理器，确保使用正确的Python环境
        from jupyter_client.kernelspec import KernelSpecManager
        ksm = KernelSpecManager()
        return ksm

    def _install_basic_packages(self):
        # 在虚拟环境中安装基本包
        # 如果是从镜像复制的环境，可能已经包含了基本包，这里可以跳过或仅检查
        try:
            # 直接使用Linux路径设置
            pip_path = os.path.join(self.venv_dir, 'bin', 'pip')
            python_exe = os.path.join(self.venv_dir, 'bin', 'python')

            # 检查ipykernel是否已安装
            check_result = subprocess.run(
                [python_exe, '-c', 'import ipykernel'],
                capture_output=True,
                text=True
            )

            # 如果ipykernel未安装，则安装
            if check_result.returncode != 0:
                print("ipykernel未安装，开始安装...")
                subprocess.check_call([pip_path, 'install', 'ipykernel'])
        except Exception as e:
            print(f"安装基础包失败: {e}")

    def execute_code(self, code: str) -> Dict:
        # 生成执行ID
        self.last_execute_id += 1

        # 执行代码
        msg_id = self.kernel_client.execute(code)

        stdout = []
        stderr = []
        error = None
        results = []

        # 收集执行结果
        while True:
            try:
                msg = self.kernel_client.get_iopub_msg(timeout=3600)
                msg_type = msg['header']['msg_type']
                if msg['parent_header'].get('msg_id') != msg_id:
                    continue 
                elif msg_type == 'stream':
                    content = msg['content']
                    if content['name'] == 'stdout':
                        stdout.append(content['text'])
                    elif content['name'] == 'stderr':
                        stderr.append(content['text'])
                elif msg_type == 'error':
                    content = msg['content']
                    # 合并error字段，包含ename、evalue和traceback
                    error = {
                        'name':ansi_escape.sub('',  content['ename']),
                        'value': ansi_escape.sub('',content['evalue']),
                        'traceback': [ansi_escape.sub('', i) for i in content['traceback']]
                    }
                elif msg_type == 'execute_result':
                    # 处理执行结果，按照{type,data}格式存储
                    data = msg['content']['data']
                    for data_type, data_value in data.items():
                        results.append({"type": data_type, "data": data_value})

                elif msg_type == 'display_data':
                    # 处理显示数据，按照{type,data}格式存储
                    data = msg['content']['data']
                    for data_type, data_value in data.items():
                        results.append({"type": data_type, "data": data_value})

                elif msg_type == 'execute_reply':
                    break
                elif msg_type == 'status':
                    if msg['content']['execution_state'] == 'idle':
                        break
            except Exception:
                break

        return {
            'stdout': [ansi_escape.sub('', i) for i in stdout],
            'stderr': [ansi_escape.sub('', i) for i in stderr],
            'error': error,
            'results': results
        }

    def upload_file(self, file: UploadFile, file_path: Optional[str] = None) -> str:
        # 确定文件保存路径：默认为工作目录最简化code
        if file_path:
            save_path = os.path.join(self.work_dir, file_path)
        else:
            save_path = os.path.join(self.work_dir, file.filename)

        # 确保目标目录存在
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # 保存文件
        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        return save_path

    def get_files(self) -> List[Dict[str, str]]:
        files = []
        for root, _, filenames in os.walk(self.work_dir):
            for filename in filenames:
                file_path = os.path.join(root, filename)
                relative_path = os.path.relpath(file_path, self.work_dir)
                files.append({
                    'path': relative_path,
                    'size': os.path.getsize(file_path)
                })
        return files

    def get_file_path(self, file_path: str) -> str:
        full_path = os.path.abspath(os.path.join(self.work_dir, file_path))
        # 安全检查，确保文件在工作目录内
        if not full_path.startswith(os.path.abspath(self.work_dir)):
            raise HTTPException(status_code=403, detail="File access denied")
        return full_path

    def shutdown(self):
        try:
            self.kernel_client.stop_channels()
            self.kernel_manager.shutdown_kernel()
            # 清理工作目录
            shutil.rmtree(self.work_dir, ignore_errors=True)
            # 清理虚拟环境目录
            shutil.rmtree(self.venv_dir, ignore_errors=True)
        except Exception:
            pass

    def install_package(self, package_name: str) -> Dict:
        """在沙箱的虚拟环境中安装Python包"""
        try:
            # 获取虚拟环境中的pip路径（Linux环境）
            pip_path = os.path.join(self.venv_dir, 'bin', 'pip')

            # 执行pip安装命令
            result = subprocess.run(
                [pip_path, 'install', package_name],
                capture_output=True,
                text=True,
                timeout=60  # 设置超时时间
            )

            # 检查安装是否成功
            if result.returncode == 0:
                return {
                    'success': True,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'message': f"成功安装包: {package_name}"
                }
            else:
                return {
                    'success': False,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'message': f"安装包失败: {package_name}"
                }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'message': f"安装过程出错: {str(e)}"
            }


# 初始化基础虚拟环境镜像
def init_base_venv_image():
    """初始化基础虚拟环境镜像，包含常用的Python包"""
    # 检查基础镜像是否存在
    if not os.path.exists(BASE_VENV_IMAGE_PATH):
        print("创建基础虚拟环境镜像...")
        # 创建基础镜像
        venv.create(BASE_VENV_IMAGE_PATH, with_pip=True)

        # 安装常用包到基础镜像（Linux环境）
        pip_path = os.path.join(BASE_VENV_IMAGE_PATH, 'bin', 'pip')

        # 安装常用包
        print(f"安装常用包到基础镜像: {', '.join(COMMON_PACKAGES)}")
        for package in COMMON_PACKAGES:
            print(f"安装 {package}...")
            try:
                subprocess.check_call([pip_path, 'install', package])
            except Exception as e:
                print(f"安装 {package} 失败: {e}")
                # 继续安装其他包
                continue

        print("基础虚拟环境镜像创建完成")
    else:
        print("基础虚拟环境镜像已存在，跳过创建")


# 创建沙箱
def create_new_sandbox() -> str:
    sandbox_id = str(uuid.uuid4())
    # 创建临时工作目录
    work_dir = tempfile.mkdtemp(prefix=f"sandbox_{sandbox_id}_")
    # 创建虚拟环境目录
    venv_dir = tempfile.mkdtemp(prefix=f"sandbox_venv_{sandbox_id}_")

    try:
        # 检查基础镜像是否存在，如果存在则复制，否则创建新的虚拟环境
        if os.path.exists(BASE_VENV_IMAGE_PATH):
            print(f"从基础镜像复制虚拟环境到 {venv_dir}")
            try:
                subprocess.check_call(['cp', '-r', os.path.join(BASE_VENV_IMAGE_PATH, '.'), venv_dir])
            except subprocess.CalledProcessError:
                print("cp命令失败，回退到使用shutil.copytree...")
                shutil.copytree(BASE_VENV_IMAGE_PATH, venv_dir)
        else:
            # 创建虚拟环境
            venv.create(venv_dir, with_pip=True)

        # 初始化沙箱
        sandbox = Sandbox(sandbox_id, work_dir, venv_dir)
        sandboxes[sandbox_id] = {
            'sandbox': sandbox,
            'created_at': asyncio.get_event_loop().time(),
            'venv_dir': venv_dir
        }
        # 启动自动关闭任务
        asyncio.create_task(auto_close_sandbox(sandbox_id))
        return sandbox_id
    except Exception as e:
        # 如果初始化失败，清理目录
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(venv_dir, ignore_errors=True)
        raise e


# 自动关闭沙箱的任务
async def auto_close_sandbox(sandbox_id: str):
    # 24小时后自动关闭沙箱（24*60*60=86400秒）
    await asyncio.sleep(86400)
    if sandbox_id in sandboxes:
        sandbox = sandboxes[sandbox_id]['sandbox']
        del sandboxes[sandbox_id]
        sandbox.shutdown()


# 检查沙箱是否存在
def get_sandbox(sandbox_id: str) -> Optional[Sandbox]:
    if sandbox_id not in sandboxes:
        return None
    return sandboxes[sandbox_id]['sandbox']


# 关闭并清理沙箱
def close_and_cleanup_sandbox(sandbox_id: str):
    if sandbox_id in sandboxes:
        sandbox = sandboxes[sandbox_id]['sandbox']
        del sandboxes[sandbox_id]
        sandbox.shutdown()


# 获取所有沙箱信息
def get_all_sandboxes_info() -> Dict[str, Dict]:
    return {sid: {"created_at": info['created_at']} for sid, info in sandboxes.items()}


# 清理过期沙箱（可定期调用）
async def cleanup_expired_sandboxes():
    current_time = asyncio.get_event_loop().time()
    # 检查每个沙箱是否超过24小时
    expired_sandboxes = [sid for sid, info in sandboxes.items()
                         if current_time - info['created_at'] > 86400]

    for sandbox_id in expired_sandboxes:
        close_and_cleanup_sandbox(sandbox_id)
