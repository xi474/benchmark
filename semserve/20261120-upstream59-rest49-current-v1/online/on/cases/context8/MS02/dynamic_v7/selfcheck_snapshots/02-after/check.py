# Packaging shim (SemServe actor runtime compatibility): delegate to the release checker.
import os
import subprocess
import sys

raise SystemExit(subprocess.call(
    [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'public_check.py')]))
