from importlib.resources import files


def test_import():
    import filescan
    pkg_root = files("filescan")

    readme = (pkg_root / "README.md").read_text(encoding="utf-8")
    readme_zh = (pkg_root / "README_zh.md").read_text(encoding="utf-8")
    license = (pkg_root / "LICENSE").read_text(encoding="utf-8")

    print(readme)
    print(readme_zh)
    print(license)
    return


def main():
    test_import()


if __name__ == "__main__":
    main()



