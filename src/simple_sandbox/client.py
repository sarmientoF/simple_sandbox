import requests
import json


class SandboxClient:
    """
    Sandbox client class for interacting with the sandbox service.
    Supports automatic cleanup: when the instance is garbage collected,
    it will automatically attempt to close the associated sandbox to prevent resource leaks.
    """

    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.sandbox_id = None

    def __del__(self):
        """Destructor that automatically closes the sandbox when the client is garbage collected"""
        if self.sandbox_id:
            try:
                self.close_sandbox()
            except Exception:
                # Avoid raising exceptions in destructor
                pass

    def create_sandbox(self):
        """Create a new sandbox instance"""
        response = requests.post(f"{self.base_url}/sandbox/create")
        if response.status_code == 200:
            self.sandbox_id = response.json()["sandbox_id"]
            print(f"✅ Sandbox created successfully, ID: {self.sandbox_id}")
            return self.sandbox_id
        else:
            print(f"❌ Failed to create sandbox: {response.text}")
            return None

    def execute_code(self, code):
        """Execute Python code in the sandbox"""
        if not self.sandbox_id:
            print("⚠️ Please create a sandbox first")
            return None

        response = requests.post(f"{self.base_url}/sandbox/{self.sandbox_id}/execute", json={"code": code})
        if response.status_code == 200:
            result = response.json()
            print("📤 Execution result:")
            if result["stdout"]:
                print(f"stdout: {result['stdout']}")
            if result["stderr"]:
                print(f"stderr: {result['stderr']}")
            if result["error"]:
                print(f"❌ Error: {result['error']}")
                print(f"Traceback: {result['traceback']}")
            return result
        else:
            print(f"❌ Failed to execute code: {response.text}")
            return None

    def install_package(self, package_name):
        """Install a Python package in the sandbox virtual environment"""
        if not self.sandbox_id:
            print("⚠️ Please create a sandbox first")
            return None

        response = requests.post(f"{self.base_url}/sandbox/{self.sandbox_id}/install",
                                 json={"package_name": package_name})
        if response.status_code == 200:
            result = response.json()
            print(f"📦 Package installed successfully: {result['message']}")
            return result
        else:
            print(f"❌ Failed to install package: {response.text}")
            return None

    def upload_file(self, file_path, target_path=None):
        """Upload a file to the sandbox"""
        if not self.sandbox_id:
            print("⚠️ Please create a sandbox first")
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
            print(f"📤 File uploaded successfully: {result['file_path']}")
            return result['file_path']
        else:
            print(f"❌ Failed to upload file: {response.text}")
            return None

    def list_files(self):
        """List all files in the sandbox"""
        if not self.sandbox_id:
            print("⚠️ Please create a sandbox first")
            return None

        response = requests.get(f"{self.base_url}/sandbox/{self.sandbox_id}/files")
        if response.status_code == 200:
            files = response.json()
            print("📁 Files in sandbox:")
            for file in files:
                print(f"- {file['path']} ({file['size']} bytes)")
            return files
        else:
            print(f"❌ Failed to get file list: {response.text}")
            return None

    def download_file(self, file_path, save_path=None):
        """Download a file from the sandbox"""
        if not self.sandbox_id:
            print("⚠️ Please create a sandbox first")
            return None

        response = requests.get(f"{self.base_url}/sandbox/{self.sandbox_id}/download/{file_path}", stream=True)
        if response.status_code == 200:
            if not save_path:
                save_path = file_path.split("/")[-1]

            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            print(f"📥 File downloaded successfully: {save_path}")
            return save_path
        else:
            print(f"❌ Failed to download file: {response.text}")
            return None

    def close_sandbox(self):
        """Close the sandbox"""
        if not self.sandbox_id:
            print("⚠️ Please create a sandbox first")
            return False

        response = requests.post(f"{self.base_url}/sandbox/{self.sandbox_id}/close")
        if response.status_code == 200:
            print("🗑️ Sandbox closed successfully")
            self.sandbox_id = None
            return True
        else:
            print(f"❌ Failed to close sandbox: {response.text}")
            return False

    def list_all_sandboxes(self):
        """List all active sandboxes (for debugging)"""
        response = requests.get(f"{self.base_url}/sandboxes")
        if response.status_code == 200:
            sandboxes = response.json()
            print("📋 Active sandboxes:")
            for sandbox_id, info in sandboxes.items():
                print(f"- {sandbox_id} (created at: {info['created_at']})")
            return sandboxes
        else:
            print(f"❌ Failed to get sandbox list: {response.text}")
            return None


# Example usage
if __name__ == "__main__":
    # Create client instance
    client = SandboxClient()

    # Create sandbox
    sandbox_id = client.create_sandbox()

    client.execute_code("print('Hello, Sandbox!')")

    # Install required Python packages in the sandbox virtual environment
    print("\n=== Installing Python packages ===")
    client.install_package("numpy")

    # Execute more complex code, e.g., use installed packages to generate a file
    client.execute_code("""
import numpy as np
import pandas as pd

# Create some data
data = {'Name': ['John', 'Anna', 'Peter', 'Linda'],
    'Age': [28, 34, 29, 42],
    'City': ['New York', 'Paris', 'Berlin', 'London']}

# Create DataFrame and save as CSV
df = pd.DataFrame(data)
df.to_csv('example_data.csv', index=False)
print('CSV file created')
    """)

    # List files in sandbox
    files = client.list_files()

    # Download the generated CSV file
    csv_file = next((f for f in files if f['path'].endswith('.csv')), None)
    client.download_file(csv_file['path'])

    # Upload a file to the sandbox
    # Note: need to create a test file first
    with open('test_upload.txt', 'w') as f:
        f.write('This is a test file for upload.')

    client.upload_file('test_upload.txt')
    client.list_files()

    # Close the sandbox
    client.close_sandbox()

    # Check if all sandboxes are closed
    client.list_all_sandboxes()
