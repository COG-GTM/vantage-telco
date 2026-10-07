import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_pyproject_pins_the_submodule_commit():
    pyproject = (ROOT / "pyproject.toml").read_text()
    pinned = re.search(r"telco-rules\.git@([0-9a-f]{40})", pyproject).group(1)
    tree = subprocess.run(
        ["git", "ls-tree", "HEAD", "third_party/telco-rules"],
        cwd=ROOT, capture_output=True, text=True, check=True,
    ).stdout.split()
    assert tree[1] == "commit"
    assert pinned == tree[2]
