from importlib.resources import files


def test_package_importable():
    import filescan

    # Ensure module has a file location
    assert hasattr(filescan, "__file__")
    assert filescan.__file__ is not None


def test_package_resources_accessible():
    pkg_root = files("filescan")

    # Ensure package root exists
    assert pkg_root.is_dir()

    # Try reading common metadata files if packaged
    for fname in ("LICENSE", "README.md", "README_zh.md"):
        p = pkg_root / fname
        if p.exists():
            text = p.read_text(encoding="utf-8")
            assert isinstance(text, str)