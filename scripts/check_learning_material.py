"""Local documentation and offline workflow checks; never sends AWS requests."""
import ast
import importlib.util
import json
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
IGNORED = {".git", ".venv", "__pycache__", "node_modules", ".local"}


def main():
    failures = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in IGNORED for part in path.relative_to(ROOT).parts):
            continue
        if path.suffix == ".py":
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        if path.suffix != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for url in re.findall(r"\[[^\]]+\]\(([^)]+)\)", text):
            if "://" in url or url.startswith("#"):
                continue
            if not (path.parent / url.split("#")[0]).resolve().exists():
                failures.append(f"{path.relative_to(ROOT)}: missing {url}")
        for language, code in re.findall(r"```(python|json|toml)\n(.*?)```", text, re.S):
            try:
                if language == "python":
                    ast.parse(code)
                elif language == "json":
                    json.loads(code)
                else:
                    tomllib.loads(code)
            except (SyntaxError, ValueError) as error:
                failures.append(f"{path.relative_to(ROOT)} {language}: {error}")
    if failures:
        raise SystemExit("\n".join(failures))
    spec = importlib.util.spec_from_file_location("learning_workflow", ROOT / "labs/cloudops-mini/workflow.py")
    workflow = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(workflow)
    start, end = workflow.today_window()
    result = workflow.run(workflow.Offline(), "cn-northwest-1", start, end)
    assert result["status"] == "succeeded"
    assert set(result["steps"]["metrics"]["result"]) == set(result["steps"]["discovery"]["result"])

    class FailedAudit(workflow.Offline):
        def audit(self):
            raise PermissionError("Synthetic audit denial")

    result = workflow.run(FailedAudit(), "cn-northwest-1", start, end)
    assert result["status"] == "partial_failure"
    assert result["steps"]["metrics"]["status"] == "succeeded"

    class FailedDiscovery(workflow.Offline):
        def discover(self):
            raise TimeoutError("Synthetic discovery timeout")

    result = workflow.run(FailedDiscovery(), "cn-northwest-1", start, end)
    assert result["steps"]["metrics"]["status"] == "skipped"
    assert result["steps"]["audit"]["status"] == "succeeded"
    print("Documentation links/snippets and offline workflow success/failure checks passed")


if __name__ == "__main__":
    main()
