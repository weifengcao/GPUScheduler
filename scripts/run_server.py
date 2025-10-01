import sys
import os

# Add the project root to the Python path.
# This is necessary so that the `uvicorn` reloader subprocess can find the `src` module.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import uvicorn

if __name__ == "__main__":
    print("--- GPUScheduler Runner ---")
    print(f"Python executable: {sys.executable}")
    print(f"Current working directory: {os.getcwd()}")
    print("Attempting to start Uvicorn server...")

    try:
        # We run the server programmatically to ensure the Python path is set correctly,
        # especially for the reloader process.
        uvicorn.run(
            "src.backend.main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            # Explicitly tell the reloader to watch our project directories.
            reload_dirs=["./src/backend", "./src/agent"],
        )
    except Exception as e:
        print("\n--- ERROR ---")
        print(f"Failed to start Uvicorn server: {e}")
        print("Please check for errors in your application code or dependencies.")
        print("---------------")