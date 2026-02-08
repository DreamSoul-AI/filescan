from importlib.resources import files


def main():
    pkg_files = list(files("filescan").iterdir())
    print([p.name for p in pkg_files])


if __name__ == "__main__":
    main()
