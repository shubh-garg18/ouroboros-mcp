"""Trust test 6: the Python Toolchain + sandbox clone (deterministic, no model).

Parsers run offline against captured sample output (no analyzers needed). Clone
and test() run for real (git + pytest are present). check() is exercised in its
fail-closed mode here, because ruff/mypy/bandit happen to be absent.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from code_fixer.sandbox import Sandbox
from code_fixer.toolchain.base import Severity
from code_fixer.toolchain.python import PythonToolchain, parse_bandit, parse_mypy, parse_ruff

SEP = "-" * 60
REPO = Path("/tmp/repo")
_failures = 0


def check(label, cond):
    global _failures
    if not cond:
        _failures += 1
    print(f"  {'PASS' if cond else 'FAIL'} — {label}")


# ---------- Part 1: parsers (offline, captured output) ----------
print(SEP)
print("Part 1: discover() parsers — captured sample output, no tools needed")

ruff_json = '[{"code":"F401","message":"`os` imported but unused","filename":"/tmp/repo/buggy.py","location":{"row":1,"column":8}}]'
ri = parse_ruff(ruff_json, REPO)
check("ruff: F401 @ line 1, path relativized to 'buggy.py', MEDIUM",
      len(ri) == 1 and ri[0].code == "F401" and ri[0].line == 1
      and ri[0].path == "buggy.py" and ri[0].severity == Severity.MEDIUM)

bandit_json = '{"results":[{"filename":"/tmp/repo/buggy.py","issue_severity":"LOW","issue_text":"Use of assert detected.","test_id":"B101","line_number":5,"col_offset":0}]}'
bi = parse_bandit(bandit_json, REPO)
check("bandit: B101 @ line 5, LOW",
      len(bi) == 1 and bi[0].code == "B101" and bi[0].line == 5 and bi[0].severity == Severity.LOW)

mypy_txt = (
    'buggy.py:7:5: error: Unsupported operand types for + ("int" and "str")  [operator]\n'
    'buggy.py:9:1: note: see documentation'
)
mi = parse_mypy(mypy_txt, REPO)
check("mypy: 'operator' error @ line 7 (note line skipped), HIGH",
      len(mi) == 1 and mi[0].code == "operator" and mi[0].line == 7 and mi[0].severity == Severity.HIGH)

ranked = sorted(ri + mi + bi, key=lambda i: (-int(i.severity), i.path, i.line))
check("ranking: mypy(HIGH) -> ruff(MEDIUM) -> bandit(LOW)",
      [i.tool for i in ranked] == ["mypy", "ruff", "bandit"])

# ---------- Part 2: sandbox clone (real git) ----------
print(SEP)
print("Part 2: Sandbox.clone — real git")

src = Path(tempfile.mkdtemp(prefix="ouro-src-"))
(src / "buggy.py").write_text("import os\n\n\ndef add(a, b):\n    return a + b\n")
(src / "test_buggy.py").write_text("from buggy import add\n\n\ndef test_add():\n    assert add(2, 3) == 5\n")


def git(*a):
    subprocess.run(
        ["git", "-C", str(src), "-c", "user.email=t@e.com", "-c", "user.name=t", *a],
        check=True, capture_output=True,
    )


git("init", "-q")
git("add", "-A")
git("commit", "-q", "-m", "init")

sb = Sandbox.create()
try:
    clone = sb.clone(str(src))
    check("clone produced buggy.py + test_buggy.py",
          (clone / "buggy.py").exists() and (clone / "test_buggy.py").exists())

    # ---------- Part 3: test() — the trust boundary ----------
    print(SEP)
    print("Part 3: test() runs pytest (the trust boundary)")
    tc = PythonToolchain(clone)
    r_pass = tc.test()
    check(f"passing suite -> test().ok (exit {r_pass.exit_code})", r_pass.ok)

    (clone / "test_broken.py").write_text("def test_broken():\n    assert 1 == 2\n")
    r_fail = tc.test()
    check(f"failing suite -> not ok (exit {r_fail.exit_code})", not r_fail.ok)

    # ---------- Part 4: check() fail-closed ----------
    print(SEP)
    print("Part 4: check() fails closed when analyzers are absent")
    cr = tc.check()
    not_found = [r.command.split()[0] for r in cr.runs if not r.found]
    check("check().ok is False when a checker isn't installed", cr.ok is False)
    print(f"     not found: {not_found or 'none (all analyzers present)'}")

    # ---------- Part 5: discover() degrades gracefully ----------
    print(SEP)
    print("Part 5: discover() degrades when analyzers absent")
    issues = tc.discover()
    check("discover() returns a list without crashing", isinstance(issues, list))
    print(f"     found {len(issues)} issue(s) with the analyzers available here")
finally:
    sb.cleanup()
    shutil.rmtree(src, ignore_errors=True)

print(SEP)
print(f"Done — {'ALL PASS' if _failures == 0 else str(_failures) + ' FAILED'}: "
      "deterministic discover/check/test; clone isolated; trust boundary fails closed.")
sys.exit(1 if _failures else 0)
