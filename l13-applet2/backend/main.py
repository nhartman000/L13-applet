import os

def run_wizard():
    print("🧠 Welcome to the L13 Applet Installer")
    port = input("Choose a port (default 8000): ") or "8000"
    print(f"\nInstalling dependencies...")
    os.system("pip install -r requirements.txt")
    print(f"\nStarting server on port {port}...")
    os.system(f"uvicorn backend.main:app --port {port} --reload")

if __name__ == "__main__":
    run_wizard()
