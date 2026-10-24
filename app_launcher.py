"""Launch Aurlex Insights with either an installed venv or the local bundled-Python fallback."""
from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / ".runtime"
os.chdir(ROOT)
if RUNTIME.is_dir():
    sys.path.insert(0, str(RUNTIME))

if len(sys.argv) < 2 or sys.argv[1] not in {"api", "ui"}:
    raise SystemExit("Usage: python app_launcher.py [api|ui]")

if sys.argv[1] == "api":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000)
else:
    from streamlit.web.cli import main
    sys.argv = [
        "streamlit", "run", str(ROOT / "frontend" / "app.py"),
        "--server.address=127.0.0.1", "--server.port=8501",
    ]
    main()
