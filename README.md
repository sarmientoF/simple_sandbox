# LLM Python Code Sandbox 🚀
> Self-Hosting an E2B-like coding playground

| Logo                                       | Description   |
|--------------------------------------------|---------------|
| <img src="./asset/logo.png" width="500px"> | A Python code sandbox HTTP service crafted for LLMs, enabling isolated Python execution environments with code execution, file operations, and MCP integration. 🎛️
|


## 🌟 Awesome Features

1. **Create Sandbox** 🆕: Spin up a Jupyter kernel and get a unique ID in a flash! ⚡
2. **Execute Code** 💻: Run code in a specified Jupyter kernel and receive stdout, stderr, errors, tracebacks, and even binary files like images. Supports Multi-Round Code Execution for complex workflows! 🎨
3. **File Operations** 📁: Upload files to the sandbox workspace and download files from it seamlessly. 📤📥
4. **Close Sandbox** 🗑️: Safely shut down sandboxes and clean up resources when you're done. ♻️
5. **Sandbox Isolation** 🔒: Each sandbox has its own Python virtual environment and working directory to prevent package conflicts. 🛡️
6. **Auto-Cleanup** 🧹: Sandboxes automatically close after 24 hours with hourly cleanup of expired ones. No messy leftovers! 🚿
7. **Virtual Environment Mirror** 🪞: Service auto-creates a base virtual environment image with common packages on startup, making new sandbox initialization super fast! ⚡
8. **MCP Support** 🤖: Integrated with FastAPI-MCP, allowing the service to be directly called by AI models. 🤝

## 🚀 Getting Started

### Install Dependencies
Run this command in your project directory to install all required packages:
```bash
cd sandbox
pip install -r requirements.txt
```

### Start the Service
Launch the sandbox service with this simple command:
```bash
python main.py --host 0.0.0.0 --port 8000
```

The service will be up and running at http://0.0.0.0:8000 🌐

## 📱 Sandbox Client (E2B-like)
You can directly use the SandboxClient to interact with the sandbox service!

### Basic Usage
```python
# Create client instance
client = SandboxClient(base_url='http://0.0.0.0:8000')

# Create a new sandbox
 sandbox_id = client.create_sandbox()

# Execute some code
client.execute_code("print('Hello, Sandbox! 👋')")

# Install required Python packages in the sandbox's virtual environment
client.install_package("numpy")

# View generated files
files = client.list_files()

# Download a generated CSV file
csv_file = next((f for f in files if f['path'].endswith('.csv')), None)
client.download_file(csv_file['path'])

# Upload a local file to the sandbox
client.upload_file('test_upload.txt')

# Close the sandbox when finished
client.close_sandbox()

# Check if all sandboxes are closed
client.list_all_sandboxes()
```

### Multi-Round Code Execution Example 🎭
The sandbox supports executing multiple code blocks in the same session, preserving state between executions. Perfect for building complex programs step by step! 🧩

```python
# Create client and sandbox
client = SandboxClient(base_url='http://0.0.0.0:8000')
client.create_sandbox()

# Step 1: Import libraries and define initial data
client.execute_code("""import numpy as np
import pandas as pd

# Create sample data
data = {
    'Name': ['Alice', 'Bob', 'Charlie', 'David'],
    'Age': [28, 32, 45, 36],
    'Salary': [8000, 12000, 15000, 9000]
}

# Create DataFrame
df = pd.DataFrame(data)
print(df)""")

# Step 2: Data processing and analysis (using data defined in step 1)
client.execute_code("""# Calculate average age and salary
avg_age = df['Age'].mean()
avg_salary = df['Salary'].mean()

print(f"Average Age: {avg_age:.1f}")
print(f"Average Salary: ${avg_age:.2f}")

# Add a new column
df['Age Group'] = pd.cut(df['Age'], bins=[20, 30, 40, 50], labels=['20-30s', '30-40s', '40-50s'])
print(df)""")


# Step 3: Save processed data
client.execute_code("""# Save to CSV file
df.to_csv('processed_data.csv', index=False)
print("Data saved to processed_data.csv 💾")
""")

# Download the generated file
files = client.list_files()
csv_file = next((f for f in files if f['path'] == 'processed_data.csv'), None)
if csv_file:
    client.download_file(csv_file['path'])

# Close the sandbox
client.close_sandbox()
```

### Matplotlib Plot Capture Example 🎨
The sandbox can capture matplotlib plots and return them as image data, perfect for displaying or saving visualizations! 📊

```python
# Create client and sandbox
client = SandboxClient(base_url='http://0.0.0.0:8000')
client.create_sandbox()

# Install required packages (if not in base environment)
client.install_package("matplotlib")
client.install_package("numpy")

# Execute plotting code
result = client.execute_code("""import numpy as np
import matplotlib.pyplot as plt

# Generate data
x = np.linspace(0, 10, 100)
y1 = np.sin(x)
y2 = np.cos(x)

# Create plot
plt.figure(figsize=(10, 6))
plt.plot(x, y1, label='Sine Function')
plt.plot(x, y2, label='Cosine Function')
plt.title('Trigonometric Functions Demo 📈')
plt.xlabel('X-axis')
plt.ylabel('Y-axis')
plt.grid(True)
plt.legend()
plt.tight_layout()

# The sandbox will automatically capture the plot and return image data
""")

# The result will contain image data for the plot, which can be used for display or saving
# Image data is typically stored in result['results'] as base64 encoded strings

# Another way to save the plot as a file
client.execute_code("""# Save the plot to a file
plt.savefig('trigonometric_functions.png', dpi=300, bbox_inches='tight')
print("Plot saved as trigonometric_functions.png 🎨")
""")

# Download the generated image file
files = client.list_files()
img_file = next((f for f in files if f['path'] == 'trigonometric_functions.png'), None)
if img_file:
    client.download_file(img_file['path'])

# Close the sandbox
client.close_sandbox()
```
