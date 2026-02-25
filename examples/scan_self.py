from pathlib import Path
from import_src import *
import filescan as fscan


def main():
    # Root directory to scan
    root = Path("../src/filescan")

    # Optional ignore file (CWD-based, same logic as CLI)
    ignore_file = Path("self.fscanignore")
    if not ignore_file.exists():
        ignore_file = None

    # Create scanner
    scanner = fscan.Scanner([root], ignore_file=ignore_file, output='output/filescan')

    # Run scan
    scanner.scan()

    # Export results
    scanner.to_csv()
    scanner.to_json()

    print("Scan completed.")
    print("Generated: filescan")

    # Create AST scanner
    ast_scanner = fscan.AstScanner([root], ignore_file=ignore_file, output="output/filescan_ast")
    # Run scan
    ast_scanner.scan()

    # Export results
    ast_scanner.to_csv()
    ast_scanner.to_json()

    print("AST scan completed.")
    print("Generated: filescan_ast")
    return


if __name__ == "__main__":
    main()
