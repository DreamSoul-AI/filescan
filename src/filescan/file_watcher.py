import threading
import time
from pathlib import Path
from typing import Optional, Set, Tuple

from watchfiles import watch, Change

from .scanner import Scanner
from .ast_scanner import AstScanner


class FileWatcher(object):

    def __init__(
        self,
        root,
        ignore_file=None,
        output=None,
        debounce_seconds=0.5,
    ):
        # type: (Path, Optional[Path], Optional[Path], float) -> None

        self.root = Path(root).resolve()
        self.ignore_file = ignore_file
        self.output = output
        self.debounce_seconds = debounce_seconds

        self._stop_event = threading.Event()
        self._last_trigger_time = 0.0

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------

    def start(self):
        # type: () -> None

        print("========================================")
        print("[watcher] Started")
        print("[watcher] Root:", self.root)
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

    def stop(self):
        # type: () -> None
        print("[watcher] Stopped.")
        self._stop_event.set()

    # ---------------------------------------------------------
    # Trigger logic
    # ---------------------------------------------------------

    def _should_trigger_filesystem_scan(self, changes):
        # type: (Set[Tuple[Change, str]]) -> bool

        for change, path_str in changes:
            if change in (Change.added, Change.deleted):
                return True
        return False

    def _should_trigger_ast_scan(self, changes):
        # type: (Set[Tuple[Change, str]]) -> bool

        for change, path_str in changes:
            if Path(path_str).suffix == ".py":
                return True
        return False

    # ---------------------------------------------------------
    # Handling
    # ---------------------------------------------------------

    def _handle_changes(self, changes, fs_trigger, ast_trigger):
        # type: (Set[Tuple[Change, str]], bool, bool) -> None

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

    def _run_filesystem_scan(self):
        # type: () -> None

        start = time.time()
        scanner = Scanner(
            root=self.root,
            ignore_file=self.ignore_file,
            output=self.output,
        )
        scanner.scan()
        scanner.to_csv(self.output)
        duration = time.time() - start
        print("[filesystem] Completed in %.3f seconds" % duration)

    def _run_ast_scan(self):
        # type: () -> None

        start = time.time()
        ast_scanner = AstScanner(
            root=self.root,
            ignore_file=self.ignore_file,
            output=self.output,
        )
        ast_scanner.scan()
        ast_scanner.to_csv(self.output)
        duration = time.time() - start
        print("[ast] Completed in %.3f seconds" % duration)