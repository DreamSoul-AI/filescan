from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # Root directory to scan
    root = Path("./data")

    # Optional ignore file (CWD-based, same logic as CLI)
    ignore_file = Path("data.fscanignore")
    if not ignore_file.exists():
        ignore_file = None

    # Create scanner
    # scanner = fscan.Scanner(root, ignore_file=ignore_file, output='output/data')
    scanner = fscan.Scanner(root, output='output/data')

    # Run scan
    scanner.scan()

    # Export results
    scanner.to_csv()   # -> ./data.csv
    scanner.to_json()  # -> ./data.json

    print("Scan completed.")
    print("Generated: data.csv, data.json")
    return


if __name__ == "__main__":
    main()
