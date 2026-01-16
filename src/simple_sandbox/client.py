import requests
import json


class SandboxClient:
    """
    沙箱客户端类，用于与沙箱服务交互。
    支持自动关闭机制：当实例被垃圾回收时，
    会自动尝试关闭关联的沙箱，防止资源泄漏。
    """

    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.sandbox_id = None

    def __del__(self):
        """析构函数，当客户端实例被垃圾回收时自动尝试关闭沙箱"""
        if self.sandbox_id:
            try:
                self.close_sandbox()
            except Exception:
                # 避免在析构函数中抛出异常
                pass

    def create_sandbox(self):
        """创建一个新的沙箱实例"""
        response = requests.post(f"{self.base_url}/sandbox/create")
        if response.status_code == 200:
            self.sandbox_id = response.json()["sandbox_id"]
            print(f"沙箱创建成功，ID: {self.sandbox_id}")
            return self.sandbox_id
        else:
            print(f"创建沙箱失败: {response.text}")
            return None

    def execute_code(self, code):
        """在沙箱中执行Python代码"""
        if not self.sandbox_id:
            print("请先创建沙箱")
            return None

        response = requests.post(f"{self.base_url}/sandbox/{self.sandbox_id}/execute", json={"code": code})
        if response.status_code == 200:
            result = response.json()
            print("执行结果:")
            if result["stdout"]:
                print(f"stdout: {result['stdout']}")
            if result["stderr"]:
                print(f"stderr: {result['stderr']}")
            if result["error"]:
                print(f"错误: {result['error']}")
                print(f"堆栈跟踪: {result['traceback']}")
            return result
        else:
            print(f"执行代码失败: {response.text}")
            return None

    def install_package(self, package_name):
        """在沙箱的虚拟环境中安装Python包"""
        if not self.sandbox_id:
            print("请先创建沙箱")
            return None

        response = requests.post(f"{self.base_url}/sandbox/{self.sandbox_id}/install",
                                 json={"package_name": package_name})
        if response.status_code == 200:
            result = response.json()
            print(f"包安装成功: {result['message']}")
            return result
        else:
            print(f"包安装失败: {response.text}")
            return None

    def upload_file(self, file_path, target_path=None):
        """上传文件到沙箱"""
        if not self.sandbox_id:
            print("请先创建沙箱")
            return None

        with open(file_path, "rb") as f:
            files = {"file": (file_path.split("/")[-1], f)}
            params = {"file_path": target_path} if target_path else {}
            response = requests.post(
                f"{self.base_url}/sandbox/{self.sandbox_id}/upload",
                files=files,
                params=params
            )

        if response.status_code == 200:
            result = response.json()
            print(f"文件上传成功: {result['file_path']}")
            return result['file_path']
        else:
            print(f"文件上传失败: {response.text}")
            return None

    def list_files(self):
        """列出沙箱中的所有文件"""
        if not self.sandbox_id:
            print("请先创建沙箱")
            return None

        response = requests.get(f"{self.base_url}/sandbox/{self.sandbox_id}/files")
        if response.status_code == 200:
            files = response.json()
            print("沙箱中的文件:")
            for file in files:
                print(f"- {file['path']} ({file['size']} bytes)")
            return files
        else:
            print(f"获取文件列表失败: {response.text}")
            return None

    def download_file(self, file_path, save_path=None):
        """从沙箱下载文件"""
        if not self.sandbox_id:
            print("请先创建沙箱")
            return None

        response = requests.get(f"{self.base_url}/sandbox/{self.sandbox_id}/download/{file_path}", stream=True)
        if response.status_code == 200:
            if not save_path:
                save_path = file_path.split("/")[-1]

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"文件下载成功: {save_path}")
            return save_path
        else:
            print(f"文件下载失败: {response.text}")
            return None

    def close_sandbox(self):
        """关闭沙箱"""
        if not self.sandbox_id:
            print("请先创建沙箱")
            return False

        response = requests.post(f"{self.base_url}/sandbox/{self.sandbox_id}/close")
        if response.status_code == 200:
            print("沙箱关闭成功")
            self.sandbox_id = None
            return True
        else:
            print(f"关闭沙箱失败: {response.text}")
            return False

    def list_all_sandboxes(self):
        """列出所有活跃的沙箱（调试用）"""
        response = requests.get(f"{self.base_url}/sandboxes")
        if response.status_code == 200:
            sandboxes = response.json()
            print("活跃的沙箱:")
            for sandbox_id, info in sandboxes.items():
                print(f"- {sandbox_id} (创建时间: {info['created_at']})")
            return sandboxes
        else:
            print(f"获取沙箱列表失败: {response.text}")
            return None


# 示例使用
if __name__ == "__main__":
    # 创建客户端实例
    client = SandboxClient()

    # 创建沙箱
    sandbox_id = client.create_sandbox()

    client.execute_code("print('Hello, Sandbox!')")

    # 在沙箱的虚拟环境中安装所需的Python包
    print("\n=== 安装Python包 ===")
    client.install_package("numpy")

    # 执行更复杂的代码，例如使用安装的包生成一个文件
    client.execute_code("""
import numpy as np
import pandas as pd

# 创建一些数据
data = {'Name': ['John', 'Anna', 'Peter', 'Linda'],
    'Age': [28, 34, 29, 42],
    'City': ['New York', 'Paris', 'Berlin', 'London']}

# 创建DataFrame并保存为CSV
df = pd.DataFrame(data)
df.to_csv('example_data.csv', index=False)
print('CSV文件已创建')
    """)

    # 列出沙箱中的文件
    files = client.list_files()

    # 下载生成的CSV文件
    csv_file = next((f for f in files if f['path'].endswith('.csv')), None)
    client.download_file(csv_file['path'])

    # 上传一个文件到沙箱
    # 注意：这里需要先创建一个测试文件
    with open('test_upload.txt', 'w') as f:
        f.write('This is a test file for upload.')

    client.upload_file('test_upload.txt')
    client.list_files()

    # 关闭沙箱
    client.close_sandbox()

    # 检查所有沙箱是否已关闭
    client.list_all_sandboxes()