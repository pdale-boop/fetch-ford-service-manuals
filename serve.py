#!/usr/bin/env python3
"""serve.py — Launch a local web server for the manual viewer."""
import sys
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 serve.py <output_dir>")
        sys.exit(1)
    output_dir = Path(sys.argv[1]).resolve()
    if not output_dir.exists():
        print(f"  ✗  Directory not found: {output_dir}")
        sys.exit(1)
    print(f"  Starting server at {output_dir}")
    print(f"  Press Ctrl+C to stop.\n")
    try:
        subprocess.run(["python3", "-m", "http.server", "8000"], cwd=output_dir)
    except KeyboardInterrupt:
        print("\n  Server stopped.")

if __name__ == "__main__":
    main()
