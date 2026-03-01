import types
from pathlib import Path

import pytest

from filescan.commands.cli import (
    cmd_scan,
    cmd_watch,
    cmd_search,
    cmd_context,
)


# =====================================================
# Helpers
# =====================================================

class DummyScanner:
    def __init__(self, *args, **kwargs):
        self.called = []

    def scan(self):
        self.called.append("scan")

    def to_csv(self):
        self.called.append("csv")

    def to_json(self):
        self.called.append("json")


class DummyWatcher:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        raise KeyboardInterrupt


class DummySearchEngine:
    def __init__(self, root, graph):
        self.root = root
        self.graph = graph

    def search(self, query):
        return [
            {
                "file": str(Path(self.root) / "a.py"),
                "line": 1,
                "text": "def foo():",
                "match_type": "definition",
                "symbol": {"qualified_name": "proj.a.foo"},
                "symbol_id": "123",
            }
        ]


class DummyBuilder:
    def __init__(self):
        self.ast = types.SimpleNamespace()
        self.ast.nodes = {"123": {"qualified_name": "proj.a.foo"}}
        self.ast.edges = []
        self.ast.by_name = {"foo": ["123"]}
        self.ast.symbols_by_file = {}
        self._has_ast = True

    def load(self, *args, **kwargs):
        return self

    def has_ast(self):
        return self._has_ast

    def extract_node_source(self, root, sid):
        return "def foo():\n    pass\n"

    def export_context_merged(self, **kwargs):
        Path(kwargs["output_path"]).write_text("merged")


# =====================================================
# SCAN COMMAND
# =====================================================

def test_cmd_scan(monkeypatch, tmp_path):
    root = tmp_path
    args = types.SimpleNamespace(
        root=str(root),
        ignore_file=None,
        ast=False,
        ast_only=False,
        output="graph",
        output_ast=None,
        format="csv",
    )

    monkeypatch.setattr("filescan.commands.cli.Scanner", DummyScanner)
    monkeypatch.setattr("filescan.commands.cli.AstScanner", DummyScanner)

    cmd_scan(args)


# =====================================================
# WATCH COMMAND
# =====================================================

def test_cmd_watch(monkeypatch, tmp_path):
    root = tmp_path
    args = types.SimpleNamespace(
        root=str(root),
        ignore_file=None,
        output="graph",
        output_ast=None,
        debounce=0.1,
    )

    monkeypatch.setattr("filescan.commands.cli.Scanner", DummyScanner)
    monkeypatch.setattr("filescan.commands.cli.AstScanner", DummyScanner)
    monkeypatch.setattr("filescan.commands.cli.FileWatcher", DummyWatcher)

    # Should not crash (KeyboardInterrupt handled)
    cmd_watch(args)


# =====================================================
# SEARCH COMMAND
# =====================================================

def test_cmd_search(monkeypatch, tmp_path, capsys):
    root = tmp_path
    nodes = tmp_path / "nodes.csv"
    edges = tmp_path / "edges.csv"

    nodes.write_text("dummy")
    edges.write_text("dummy")

    args = types.SimpleNamespace(
        root=str(root),
        query="foo",
        nodes=str(nodes),
        edges=str(edges),
    )

    monkeypatch.setattr("filescan.commands.cli.GraphBuilder", DummyBuilder)
    monkeypatch.setattr("filescan.commands.cli.SearchEngine", DummySearchEngine)

    cmd_search(args)

    captured = capsys.readouterr()
    assert "DEFINITION" in captured.out
    assert "proj.a.foo" in captured.out


# =====================================================
# CONTEXT COMMAND
# =====================================================

def test_cmd_context(monkeypatch, tmp_path, capsys):
    fs_nodes = tmp_path / "fs_nodes.csv"
    fs_edges = tmp_path / "fs_edges.csv"

    fs_nodes.write_text("dummy")
    fs_edges.write_text("dummy")

    out = tmp_path / "out.txt"

    args = types.SimpleNamespace(
        fs_nodes=str(fs_nodes),
        fs_edges=str(fs_edges),
        ast_nodes=None,
        ast_edges=None,
        output=str(out),
    )

    monkeypatch.setattr("filescan.commands.cli.GraphBuilder", DummyBuilder)

    cmd_context(args)

    captured = capsys.readouterr()
    assert "Wrote context to" in captured.out
    assert out.exists()