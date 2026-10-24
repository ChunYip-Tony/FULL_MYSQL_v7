"""Run the canonical rebuild-scope regressions used by both CI entrypoints."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    runpy.run_path(str(Path(__file__).resolve().parents[1] / "server" / "test_routine_pos_scope.py"),
                  run_name="__main__")

