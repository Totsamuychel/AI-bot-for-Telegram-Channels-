import os
from dotenv import load_dotenv

load_dotenv()

# Name shown in orchestrator logs
WORKER_NAME: str = os.getenv("WORKER_NAME", "worker-1")
# Port this worker listens on
WORKER_PORT: int = int(os.getenv("WORKER_PORT", "8010"))
# Secret shared with orchestrator to authenticate incoming tasks
WORKER_AUTH_TOKEN: str = os.getenv("WORKER_AUTH_TOKEN", "")
# Orchestrator URL — used only if this worker should auto-register (optional)
ORCHESTRATOR_URL: str = os.getenv("ORCHESTRATOR_URL", "")
