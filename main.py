import subprocess
import sys
import time
import os

def main():
    print("=======================================================")
    print("  🚀 Starting InsightOS (Backend + Frontend)...")
    print("=======================================================")

    root_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_dir = os.path.join(root_dir, "insight-agent")

    # Start the backend (FastAPI via Uvicorn)
    print("-> Starting InsightOS Backend API (Uvicorn)...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
        cwd=root_dir
    )

    # Start the frontend (Vite/React)
    print("-> Starting InsightOS Frontend (Vite)...")
    frontend_process = subprocess.Popen(
        ["npm", "run", "dev"],
        cwd=frontend_dir,
        shell=True
    )

    print("\n=======================================================")
    print("  🖥️  InsightOS Frontend:  http://localhost:5173")
    print("  ⚙️  InsightOS Backend API: http://localhost:8000")
    print("  📖 API Documentation:    http://localhost:8000/docs")
    print("  Press Ctrl+C to stop both servers.")
    print("=======================================================\n")

    try:
        while True:
            time.sleep(1)
            if backend_process.poll() is not None or frontend_process.poll() is not None:
                print("\nOne of the servers has stopped. Shutting down...")
                break
    except KeyboardInterrupt:
        print("\nStopping InsightOS servers...")
    finally:
        if backend_process.poll() is None:
            backend_process.terminate()
            try:
                backend_process.wait(timeout=5)
            except Exception:
                backend_process.kill()
            print("Backend server stopped.")
        
        if frontend_process.poll() is None:
            subprocess.call(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)], stderr=subprocess.DEVNULL)
            print("Frontend server stopped.")

    print("Goodbye!")

if __name__ == "__main__":
    main()
