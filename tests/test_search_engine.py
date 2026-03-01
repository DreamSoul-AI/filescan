from pathlib import Path

from filescan.graph_builder import GraphBuilder
from filescan.search_engine import SearchEngine


# =====================================================
# HELPER: build search engine with fake grep
# =====================================================

def build_engine(tmp_path, file_content_map):
    root = tmp_path / "proj"
    root.mkdir()

    for name, content in file_content_map.items():
        (root / name).write_text(content)

    builder = GraphBuilder()
    builder.build([root], include_ast=True)

    engine = SearchEngine(root, builder.ast)
    return root, engine


# =====================================================
# TEST: definition match type
# =====================================================

def test_search_definition(tmp_path, monkeypatch):
    root, engine = build_engine(
        tmp_path,
        {
            "a.py": "def foo():\n    pass\n"
        },
    )

    # Fake ripgrep match
    monkeypatch.setattr(
        engine,
        "_grep",
        lambda query: [
            {
                "file": str(root / "a.py"),
                "line": 1,
                "text": "def foo():\n",
            }
        ],
    )

    results = engine.search("foo")

    assert len(results) == 1
    assert results[0]["match_type"] == "definition"


# =====================================================
# TEST: semantic reference match
# =====================================================

def test_search_reference(tmp_path, monkeypatch):
    root, engine = build_engine(
        tmp_path,
        {
            "a.py": "def foo():\n    pass\n",
            "b.py": "from proj.a import foo\n\ndef bar():\n    foo()\n",
        },
    )

    monkeypatch.setattr(
        engine,
        "_grep",
        lambda query: [
            {
                "file": str(root / "b.py"),
                "line": 4,
                "text": "    foo()\n",
            }
        ],
    )

    results = engine.search("foo")

    assert len(results) == 1
    assert results[0]["match_type"] in {"references", "calls"}


# =====================================================
# TEST: unknown match type
# =====================================================

def test_search_unknown(tmp_path, monkeypatch):
    root, engine = build_engine(
        tmp_path,
        {
            "a.py": "def foo():\n    pass\n"
        },
    )

    monkeypatch.setattr(
        engine,
        "_grep",
        lambda query: [
            {
                "file": str(root / "a.py"),
                "line": 2,
                "text": "    pass\n",
            }
        ],
    )

    results = engine.search("pass")

    assert len(results) == 1
    assert results[0]["match_type"] == "unknown"


# =====================================================
# TEST: result sorting priority
# =====================================================

def test_search_priority_sorting(tmp_path, monkeypatch):
    root, engine = build_engine(
        tmp_path,
        {
            "a.py": "def foo():\n    foo()\n"
        },
    )

    monkeypatch.setattr(
        engine,
        "_grep",
        lambda query: [
            {
                "file": str(root / "a.py"),
                "line": 2,
                "text": "    foo()\n",
            },
            {
                "file": str(root / "a.py"),
                "line": 1,
                "text": "def foo():\n",
            },
        ],
    )

    results = engine.search("foo")

    # Definition should come before calls/references
    assert results[0]["match_type"] == "definition"