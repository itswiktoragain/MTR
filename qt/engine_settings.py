import os
import sys
from pathlib import Path

BASE = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'MTR' / 'Engine'
BUNDLE = (Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent / 'publish') / 'clamav'
MAX_FILE = 64 * 1024 * 1024
