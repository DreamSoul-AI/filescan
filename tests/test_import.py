import os
import sys
from importlib.resources import files


def test_import():
    import filescan
    pkg_root = files("filescan")

    # Not all packaging modes include extra data files; ensure import works and
    # at least the package directory is accessible.
    assert pkg_root.exists()
    # try reading license if present, but don't fail the test if it's missing
    for fname in ("LICENSE", "README.md", "README_zh.md"):
        p = pkg_root / fname
        if p.exists():
            _ = p.read_text(encoding="utf-8")
    return


def main():
    test_import()


if __name__ == "__main__":
    main()



