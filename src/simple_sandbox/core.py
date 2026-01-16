import os
import uuid
import asyncio
import shutil
import subprocess
from typing import Dict, Optional, List
from fastapi import UploadFile, HTTPException
from jupyter_client import KernelManager
import tempfile
import re
from importlib import resources

# Filter ANSI escape sequences from jupyter output
ansi_escape = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')

# Store all sandbox instances
sandboxes: Dict[str, Dict] = {}

# Base venv image path (created at runtime in temp directory)
BASE_VENV_IMAGE_PATH = os.path.join(tempfile.gettempdir(), "simple_sandbox_base_venv")

# Common data analysis packages
COMMON_PACKAGES = ['ipykernel', 'numpy', 'pandas', 'matplotlib', 'scipy', 'seaborn']

# Matplotlib Chinese font support code
font_code = """import os
import matplotlib as mpl
import matplotlib.font_manager as fm

# Register custom font
font_path = os.path.join(os.getcwd(), 'SimHei.ttf')
if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    font_name = fm.FontProperties(fname=font_path).get_name()
    mpl.rcParams['font.sans-serif'] = [font_name] + mpl.rcParams['font.sans-serif']
    mpl.rcParams['font.family'] = 'sans-serif'
"""


def get_font_path() -> Optional[str]:
    """Get the path to the bundled SimHei.ttf font file."""
    try:
        font_file = resources.files('simple_sandbox.assets').joinpath('SimHei.ttf')
        # For Python 3.9+, use as_file to get actual path
        with resources.as_file(font_file) as path:
            return str(path)
    except Exception:
        return None


class Sandbox:
    def __init__(self, sandbox_id: str, work_dir: str, venv_dir: str):
        self.sandbox_id = sandbox_id
        self.work_dir = work_dir
        self.venv_dir = venv_dir

        # Configure KernelManager to use virtual environment Python interpreter
        self.kernel_manager = KernelManager(
            kernel_name='python3',
            kernel_spec_manager=self._create_custom_kernel_spec_manager()
        )
        # Set environment variables
        env = os.environ.copy()
        env['VIRTUAL_ENV'] = venv_dir

        # Start kernel using virtual environment Python
        self.kernel_manager.start_kernel(
            cwd=work_dir,
            env=env,
        )

        self.kernel_client = self.kernel_manager.client()
        self.kernel_client.start_channels()
        self.kernel_client.wait_for_ready()
        self.last_execute_id = 0

        # Copy font file to sandbox work directory
        font_source_path = get_font_path()
        font_dest_path = os.path.join(work_dir, 'SimHei.ttf')
        if font_source_path and os.path.exists(font_source_path):
            try:
                shutil.copy2(font_source_path, font_dest_path)
                print(f"Font file copied to: {font_dest_path}")
            except Exception as e:
                print(f"Failed to copy font file: {e}")
        else:
            print(f"Font file not found: {font_source_path}")

        # Install basic packages
        self._install_basic_packages()

        # Execute font registration code
        self.execute_code(font_code)

    def _create_custom_kernel_spec_manager(self):
        from jupyter_client.kernelspec import KernelSpecManager
        ksm = KernelSpecManager()
        return ksm

    def _install_basic_packages(self):
        """Install basic packages in the virtual environment using uv."""
        try:
            python_exe = os.path.join(self.venv_dir, 'bin', 'python')

            # Check if ipykernel is already installed
            check_result = subprocess.run(
                [python_exe, '-c', 'import ipykernel'],
                capture_output=True,
                text=True
            )

            # If ipykernel is not installed, install it
            if check_result.returncode != 0:
                print("ipykernel not installed, installing...")
                subprocess.check_call([
                    'uv', 'pip', 'install',
                    '--python', python_exe,
                    'ipykernel'
                ])
        except Exception as e:
            print(f"Failed to install basic packages: {e}")

    def execute_code(self, code: str) -> Dict:
        """Execute Python code in the sandbox."""
        self.last_execute_id += 1

        msg_id = self.kernel_client.execute(code)

        stdout = []
        stderr = []
        error = None
        results = []

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
                    error = {
                        'name': ansi_escape.sub('', content['ename']),
                        'value': ansi_escape.sub('', content['evalue']),
                        'traceback': [ansi_escape.sub('', i) for i in content['traceback']]
                    }
                elif msg_type == 'execute_result':
                    data = msg['content']['data']
                    for data_type, data_value in data.items():
                        results.append({"type": data_type, "data": data_value})
                elif msg_type == 'display_data':
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
        """Upload a file to the sandbox."""
        if file_path:
            save_path = os.path.join(self.work_dir, file_path)
        else:
            save_path = os.path.join(self.work_dir, file.filename)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        return save_path

    def get_files(self) -> List[Dict[str, str]]:
        """Get list of files in the sandbox."""
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
        """Get the full path of a file in the sandbox."""
        full_path = os.path.abspath(os.path.join(self.work_dir, file_path))
        if not full_path.startswith(os.path.abspath(self.work_dir)):
            raise HTTPException(status_code=403, detail="File access denied")
        return full_path

    def shutdown(self):
        """Shutdown the sandbox and cleanup resources."""
        try:
            self.kernel_client.stop_channels()
            self.kernel_manager.shutdown_kernel()
            shutil.rmtree(self.work_dir, ignore_errors=True)
            shutil.rmtree(self.venv_dir, ignore_errors=True)
        except Exception:
            pass

    def install_package(self, package_name: str) -> Dict:
        """Install a Python package in the sandbox virtual environment using uv."""
        try:
            python_exe = os.path.join(self.venv_dir, 'bin', 'python')

            result = subprocess.run(
                ['uv', 'pip', 'install', '--python', python_exe, package_name],
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode == 0:
                return {
                    'success': True,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'message': f"Successfully installed package: {package_name}"
                }
            else:
                return {
                    'success': False,
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'message': f"Failed to install package: {package_name}"
                }
        except Exception as e:
            return {
                'success': False,
                'stdout': '',
                'stderr': str(e),
                'message': f"Installation error: {str(e)}"
            }


def init_base_venv_image():
    """Initialize the base virtual environment image with common packages using uv."""
    if not os.path.exists(BASE_VENV_IMAGE_PATH):
        print("Creating base virtual environment image...")

        # Create base venv using uv
        subprocess.check_call(['uv', 'venv', BASE_VENV_IMAGE_PATH])

        python_exe = os.path.join(BASE_VENV_IMAGE_PATH, 'bin', 'python')

        # Install common packages
        print(f"Installing common packages: {', '.join(COMMON_PACKAGES)}")
        for package in COMMON_PACKAGES:
            print(f"Installing {package}...")
            try:
                subprocess.check_call([
                    'uv', 'pip', 'install',
                    '--python', python_exe,
                    package
                ])
            except Exception as e:
                print(f"Failed to install {package}: {e}")
                continue

        print("Base virtual environment image created successfully")
    else:
        print("Base virtual environment image already exists, skipping creation")


def create_new_sandbox() -> str:
    """Create a new sandbox instance."""
    sandbox_id = str(uuid.uuid4())
    work_dir = tempfile.mkdtemp(prefix=f"sandbox_{sandbox_id}_")
    venv_dir = tempfile.mkdtemp(prefix=f"sandbox_venv_{sandbox_id}_")

    try:
        # Copy from base image if exists, otherwise create new venv
        if os.path.exists(BASE_VENV_IMAGE_PATH):
            print(f"Copying virtual environment from base image to {venv_dir}")
            try:
                subprocess.check_call(['cp', '-r', os.path.join(BASE_VENV_IMAGE_PATH, '.'), venv_dir])
            except subprocess.CalledProcessError:
                print("cp command failed, falling back to shutil.copytree...")
                shutil.rmtree(venv_dir, ignore_errors=True)
                shutil.copytree(BASE_VENV_IMAGE_PATH, venv_dir)
        else:
            # Create new venv using uv
            subprocess.check_call(['uv', 'venv', venv_dir])

        sandbox = Sandbox(sandbox_id, work_dir, venv_dir)
        sandboxes[sandbox_id] = {
            'sandbox': sandbox,
            'created_at': asyncio.get_event_loop().time(),
            'venv_dir': venv_dir
        }
        asyncio.create_task(auto_close_sandbox(sandbox_id))
        return sandbox_id
    except Exception as e:
        shutil.rmtree(work_dir, ignore_errors=True)
        shutil.rmtree(venv_dir, ignore_errors=True)
        raise e


async def auto_close_sandbox(sandbox_id: str):
    """Automatically close sandbox after 24 hours."""
    await asyncio.sleep(86400)
    if sandbox_id in sandboxes:
        sandbox = sandboxes[sandbox_id]['sandbox']
        del sandboxes[sandbox_id]
        sandbox.shutdown()


def get_sandbox(sandbox_id: str) -> Optional[Sandbox]:
    """Get a sandbox by ID."""
    if sandbox_id not in sandboxes:
        return None
    return sandboxes[sandbox_id]['sandbox']


def close_and_cleanup_sandbox(sandbox_id: str):
    """Close and cleanup a sandbox."""
    if sandbox_id in sandboxes:
        sandbox = sandboxes[sandbox_id]['sandbox']
        del sandboxes[sandbox_id]
        sandbox.shutdown()


def get_all_sandboxes_info() -> Dict[str, Dict]:
    """Get information about all active sandboxes."""
    return {sid: {"created_at": info['created_at']} for sid, info in sandboxes.items()}


async def cleanup_expired_sandboxes():
    """Cleanup sandboxes that have exceeded 24 hours."""
    current_time = asyncio.get_event_loop().time()
    expired_sandboxes = [sid for sid, info in sandboxes.items()
                         if current_time - info['created_at'] > 86400]

    for sandbox_id in expired_sandboxes:
        close_and_cleanup_sandbox(sandbox_id)
