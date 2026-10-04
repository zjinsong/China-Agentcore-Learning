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

    # 离线校验最小 harness:正常依赖链、上游失败跳过、计划校验。
    spec = importlib.util.spec_from_file_location("harness", ROOT / "05-harness/harness.py")
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)

    ok = harness.run([
        {"tool": "get_weather", "args": {"city": "上海"}, "depends_on": []},
        {"tool": "suggest_outfit", "depends_on": [0]},
    ])
    assert ok[0]["status"] == "succeeded" and ok[1]["status"] == "succeeded"

    bad = harness.run([
        {"tool": "get_weather", "args": {"city": "广州"}, "depends_on": []},
        {"tool": "suggest_outfit", "depends_on": [0]},
    ])
    assert bad[0]["status"] == "failed" and bad[1]["status"] == "failed"

    for plan in (
        [{"tool": "不存在", "depends_on": []}],
        [{"tool": "get_weather", "depends_on": [1]}, {"tool": "suggest_outfit", "depends_on": [0]}],
    ):
        try:
            harness.validate(plan)
            raise AssertionError("非法计划未被拦截")
        except ValueError:
            pass

    print("Documentation links/snippets and offline harness success/failure checks passed")


if __name__ == "__main__":
    main()
