import threading
import time
from pathlib import Path
from typing import Optional, Set, Tuple, Union, List

from watchfiles import watch, Change

from .graph_builder import GraphBuilder

PathLike = Union[str, Path]


class FileWatcher:
    """
    Incremental File Watcher using persistent GraphBuilder.

    Behavior:
    - Filesystem graph updated only for added/deleted paths
    - AST graph updated only for changed .py files
    - Deleted paths removed from both graphs
    - No full rebuild after initial build
    """

    # ==========================================================
    # Initialization
    # ==========================================================

    def __init__(
        self,
        root: PathLike,
        ignore_file: Optional[PathLike] = None,
        output: Optional[PathLike] = None,
        debounce_seconds: float = 0.5,
    ) -> None:

        self.root = Path(root).resolve()
        self.ignore_file = Path(ignore_file).resolve() if ignore_file else None

        base = Path(output).resolve() if output else Path("output").resolve()

        self.output_fs = base
        self.output_ast = base.with_name(base.name + "_ast")
        self.output_context = base.with_name(base.name + "_context.txt")

        self.debounce_seconds = float(debounce_seconds)

        self._stop_event = threading.Event()
        self._last_trigger_time = 0.0

        self.builder = GraphBuilder()

    # ==========================================================
    # Public API
    # ==========================================================

    def start(self) -> None:
        """
        Start watching and perform initial full build.
        """

        print("========================================")
        print("[watcher] Started")
        print("[watcher] Root      :", self.root)
        print("[watcher] Output FS :", self.output_fs)
        print("[watcher] Output AST:", self.output_ast)
        print("========================================\n")

        # Initial full build
        self.builder.build(
            [self.root],
            ignore_file=self.ignore_file,
            include_filesystem=True,
            include_ast=True,
        )

        # Export initial state
        self._export_all()

        print("[watcher] Initial build complete\n")

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

    # ==========================================================
    # Export Helper
    # ==========================================================

    def _export_all(self) -> None:

        # 1️⃣ Export filesystem
        self.builder.export_filesystem(self.output_fs)

        # 2️⃣ Export AST
        self.builder.export_ast(self.output_ast)

        # Build actual generated CSV paths
        fs_nodes = self.output_fs.with_name(self.output_fs.name + "_nodes.csv")
        fs_edges = self.output_fs.with_name(self.output_fs.name + "_edges.csv")

        ast_nodes = self.output_ast.with_name(self.output_ast.name + "_nodes.csv")
        ast_edges = self.output_ast.with_name(self.output_ast.name + "_edges.csv")

        # 3️⃣ Merge everything into one context file
        self.builder.export_context_merged(
            self.output_context,
            fs_nodes_path=fs_nodes,
            fs_edges_path=fs_edges,
            ast_nodes_path=ast_nodes,
            ast_edges_path=ast_edges,
        )

        print("[watcher] Exported merged context ->", self.output_context)

    # ==========================================================
    # Trigger Logic
    # ==========================================================

    def _should_trigger_filesystem_scan(
        self, changes: Set[Tuple[Change, str]]
    ) -> bool:
        return any(change in (Change.added, Change.deleted) for change, _ in changes)

    def _should_trigger_ast_scan(
        self, changes: Set[Tuple[Change, str]]
    ) -> bool:
        return any(Path(path).suffix == ".py" for _, path in changes)

    # ==========================================================
    # Change Handling (Incremental)
    # ==========================================================

    def _handle_changes(
            self,
            changes: Set[Tuple[Change, str]],
            fs_trigger: bool,
            ast_trigger: bool,
    ) -> None:

        print("\n----------------------------------------")
        print("[watcher] Change detected at", time.strftime("%H:%M:%S"))
        print("[watcher] Total events:", len(changes))

        added_or_modified: List[Path] = []
        deleted: List[Path] = []

        for change, path_str in changes:
            path = Path(path_str).resolve()
            print("  -", change.name, ":", path)

            if change == Change.deleted:
                deleted.append(path)
            else:
                added_or_modified.append(path)

        graph_changed = False

        # ----------------------------------------
        # Handle deletions
        # ----------------------------------------

        if deleted:
            print("\n>>> Removing deleted paths")
            self.builder.remove_paths(deleted)
            graph_changed = True

        # ----------------------------------------
        # Filesystem partial update
        # ----------------------------------------

        if fs_trigger and added_or_modified:
            print("\n>>> Filesystem partial update")
            self.builder.update_filesystem_paths(
                added_or_modified,
                ignore_file=self.ignore_file,
            )
            graph_changed = True

        # ----------------------------------------
        # AST partial update
        # ----------------------------------------

        py_paths = [p for p in added_or_modified if p.suffix == ".py"]

        if ast_trigger and py_paths:
            print("\n>>> AST partial update")
            self.builder.update_ast_paths(
                py_paths,
                ignore_file=self.ignore_file,
            )
            graph_changed = True

        # ----------------------------------------
        # Export only if changed
        # ----------------------------------------

        if graph_changed:
            print("\n>>> Exporting updated graphs")
            self._export_all()
            print(">>> Export complete")

        print("----------------------------------------\n")