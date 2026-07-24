import os
import subprocess
import tempfile

def execute_python_code(code: str) -> str:
    """Executes a snippet of python code and returns the stdout/stderr."""
    # Find the python interpreter in the virtual environment
    venv_python = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "venv", "bin", "python")
    
    # If not found, fallback to system python
    if not os.path.exists(venv_python):
        venv_python = "python3"
        
    try:
        # Write the code to a temporary file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp_file:
            temp_file.write(code)
            temp_path = temp_file.name

        # Set up environment to silence Matplotlib warnings about config dir
        env = os.environ.copy()
        env["MPLCONFIGDIR"] = tempfile.gettempdir()

        # Execute it
        result = subprocess.run([venv_python, temp_path], capture_output=True, text=True, timeout=30, env=env)
        
        output = result.stdout
        if result.stderr:
            output += "\nError Output:\n" + result.stderr
            
        # Clean up
        os.unlink(temp_path)
        
        return output.strip() if output else "Code executed successfully with no output."
    except subprocess.TimeoutExpired:
        return "Execution Error: Python code timed out after 30 seconds."
    except Exception as e:
        return f"Execution Error: {str(e)}"
