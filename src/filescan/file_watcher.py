import threading
import time
from pathlib import Path
from typing import Optional, Set, Tuple, Union

from watchfiles import watch, Change

from .scanner import Scanner
from .ast_scanner import AstScanner


PathLike = Union[str, Path]


class FileWatcher:
    """
    Watches a root directory and triggers:
      - filesystem scan on add/delete events
      - AST scan on any .py change event

    Output behavior:

    If `output` is provided:
        filesystem -> <output>
        AST        -> <output>_ast

    If `output` is None:
        filesystem -> ./output
        AST        -> ./output_ast
    """

    def __init__(
        self,
        root: PathLike,
        ignore_file: Optional[PathLike] = None,
        output: Optional[PathLike] = None,
        debounce_seconds: float = 0.5,
    ) -> None:

        self.root = Path(root).resolve()

        self.ignore_file = (
            Path(ignore_file).resolve() if ignore_file else None
        )

        # ------------------------------
        # Output handling (clean logic)
        # ------------------------------
        if output is not None:
            base = Path(output).resolve()
        else:
            base = Path("output").resolve()

        self.output_fs = base
        self.output_ast = base.with_name(base.name + "_ast")

        self.debounce_seconds = float(debounce_seconds)
        self._stop_event = threading.Event()
        self._last_trigger_time = 0.0

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def start(self) -> None:
        print("========================================")
        print("[watcher] Started")
        print("[watcher] Root      :", self.root)
        print("[watcher] Output FS :", self.output_fs)
        print("[watcher] Output AST:", self.output_ast)
        print("========================================\n")

        for changes in watch(self.root, recursive=True):
            if self._stop_event.is_set():
                break

            now = time.time()
            if now - self._last_trigger_time < self.debounce_seconds:
                continue

            fs_trigger = self._should_trigger_filesystem_scan(changes)
            ast_trigger = self._should_trigger_ast_scan(changes)

            if not fs_trigger and not ast_trigger:
                continue

            self._last_trigger_time = now
            self._handle_changes(changes, fs_trigger, ast_trigger)

    def stop(self) -> None:
        self._stop_event.set()

    # ---------------------------------------------------------
    # Trigger logic
    # ---------------------------------------------------------

    def _should_trigger_filesystem_scan(
        self, changes: Set[Tuple[Change, str]]
    ) -> bool:
        for change, _ in changes:
            if change in (Change.added, Change.deleted):
                return True
        return False

    def _should_trigger_ast_scan(
        self, changes: Set[Tuple[Change, str]]
    ) -> bool:
        for _, path_str in changes:
            if Path(path_str).suffix == ".py":
                return True
        return False

    # ---------------------------------------------------------
    # Handling
    # ---------------------------------------------------------

    def _handle_changes(
        self,
        changes: Set[Tuple[Change, str]],
        fs_trigger: bool,
        ast_trigger: bool,
    ) -> None:

        print("\n----------------------------------------")
        print("[watcher] Change detected at", time.strftime("%H:%M:%S"))
        print("[watcher] Total events:", len(changes))

        for change, path in changes:
            print("  -", change.name, ":", path)

        if fs_trigger:
            print("\n>>> Filesystem scan TRIGGERED")
            self._run_filesystem_scan()
            print(">>> Filesystem scan FINISHED")

        if ast_trigger:
            print("\n>>> AST semantic scan TRIGGERED")
            self._run_ast_scan()
            print(">>> AST semantic scan FINISHED")

        print("----------------------------------------\n")

    # ---------------------------------------------------------
    # Scan execution
    # ---------------------------------------------------------

    def _run_filesystem_scan(self) -> None:
        start = time.time()

        scanner = Scanner(
            root=self.root,
            ignore_file=self.ignore_file,
            output=self.output_fs,
        )
        scanner.scan()
        scanner.to_csv()

        print("[filesystem] Completed in %.3f seconds" % (time.time() - start))

    def _run_ast_scan(self) -> None:
        start = time.time()

        ast_scanner = AstScanner(
            root=self.root,
            ignore_file=self.ignore_file,
            output=self.output_ast,
        )
        ast_scanner.scan()
        ast_scanner.to_csv()

        print("[ast] Completed in %.3f seconds" % (time.time() - start))