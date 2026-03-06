# filescan

**filescan** is a Python tool for analyzing code at scale through **flat graph representations**.

Scan two layers of your codebase and export them as graph data:

* **📁 Filesystem Graph**: Directory structure → parent/child relationships
* **🧠 Python AST Graph**: Python source code → modules, classes, functions, and cross-file semantic relationships

Instead of nested trees, `filescan` produces **flat node and edge tables** (CSV/JSON) suitable for:

- 🔍 **SQL and Pandas analysis**
- 🤖 **LLM code understanding (token-efficient)**
- 📊 **Static analysis pipelines**
- 🗂️ **Graph algorithms and embeddings**

---

## Why Flat Graphs?

Traditional nested JSON/tree structures are:

- 📈 Verbose and deeply nested
- 🚩 Hard to filter, join, or aggregate
- 💰 Expensive for LLM token usage
- ⚠️ Inefficient for large codebases

`filescan` instead uses **explicit node and edge tables**:

```
nodes.csv     (id, type/kind, name, metadata...)
edges.csv     (id, source, target, relation, ...)
```

**Benefits:**
- ✅ Materialize relationships explicitly
- ✅ Works naturally with SQL, Pandas, DuckDB
- ✅ Lower token overhead for LLMs
- ✅ Great for graph algorithms
- ✅ Deterministic and reproducible

---

## Features

### 📁 Filesystem Scanner

- Recursive directory traversal in deterministic order
- Parent → child edge relationships
- File size and metadata
- Supports `.gitignore`-style ignore rules (`.fscanignore`)
- CSV + JSON export
- Deterministic, collision-safe node IDs

### 🧠 Python AST Scanner

- **Definitions**: Modules, classes, functions, methods
- **Docstrings**: First-line capture for context
- **Signatures**: Function/method parameters (best-effort)
- **Line numbers**: Exact source locations
- **Cross-file relationships**:
  - `contains` — class contains method
  - `imports` — module imports symbol
  - `calls` — function calls another function
  - `inherits` — class inherits from base class
  - `references` — any other reference

### ⚙️ Core Capabilities

- Multi-root scanning support
- Unified programmatic API
- CLI with multiple commands (`scan`, `watch`, `search`, `context`, `uml`)
- File watcher with auto-rescan
- Hybrid text + semantic search
- Built-in ignore rules (Python-aware defaults)

---

## Installation

### From PyPI

```bash
pip install filescan
```

### Development Mode

```bash
git clone https://github.com/DreamSoul-AI/filescan.git
cd filescan
pip install -e .
```

**Requirements:** Python 3.10+

---

## Quick Start

### CLI: Scan a Directory

```bash
# Scan filesystem structure
filescan scan ./src

# Include Python AST analysis
filescan scan ./src --ast

# Custom output location
filescan scan ./src --ast -o results/myproject
```

**Output:**
```
results/
├── myproject_nodes.csv
├── myproject_edges.csv
├── myproject.json
├── myproject_ast_nodes.csv
├── myproject_ast_edges.csv
└── myproject_ast.json
```

### CLI: Watch Mode (Auto-Rescan)

```bash
filescan watch ./src --debounce 0.5
```

Re-scans automatically when `.py` files change. Useful during development.

### CLI: Semantic Search

```bash
filescan search ./src "MyClass" \
  --nodes graph_ast_nodes.csv \
  --edges graph_ast_edges.csv
```

Finds all references to `MyClass` in the codebase with semantic context.

### CLI: Export Mermaid UML

```bash
filescan uml ./src -o results/uml.md
```

---

## Library Usage
## Filesystem Scanner

```python
from filescan import GraphBuilder

builder = GraphBuilder()
builder.build(roots=["./data"], include_filesystem=True, include_ast=False)
builder.export_filesystem("output/fs")

print(f"Found {len(builder.filesystem.nodes)} filesystem nodes")
```

## Python AST Scanner

```python
from filescan import GraphBuilder

# Build and export
builder = GraphBuilder()
builder.build(roots=["./src"], include_filesystem=False, include_ast=True, ignore_file=".fscanignore")
builder.export_ast("output/ast")

print(f"Indexed symbols: {len(builder.ast.by_qname)}")
```

## Advanced: GraphBuilder

```python
from filescan import GraphBuilder
from pathlib import Path

# Single-pass builder for both graphs
builder = GraphBuilder()

builder.build(
    roots=[Path("./src"), Path("./tests")],  # Multiple roots
    include_filesystem=True,
    include_ast=True,
    ignore_file=".fscanignore"
)

# Export with custom prefixes
builder.export_filesystem("output/fs")
builder.export_ast("output/ast")

# Access graph data programmatically
fs_nodes = builder.filesystem.nodes
fs_edges = list(builder.filesystem.edges)
ast_nodes = builder.ast.nodes
ast_edges = list(builder.ast.edges)
```

---

## Ignore Rules (`.fscanignore`)

`filescan` supports **gitignore-style patterns** via `pathspec`.

### Resolution order:

1. `--ignore-file` CLI argument (if provided)
2. `./.fscanignore` in working directory (if exists)
3. Built-in defaults (ignore `.git`, `__pycache__`, `.pyc`, etc.)

### Example `.fscanignore`:

```gitignore
# Version control
.git/
.hg/

# IDEs
.vscode/
.idea/
*.swp

# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
.venv/
venv/

# Build & dist
build/
dist/
*.egg

# Project-specific
node_modules/
.DS_Store
```

Patterns apply to both **filesystem and AST scanning** (ignored files are skipped).

---

## Output Schemas

### Filesystem Graph

**Nodes** (`*_nodes.csv`):

| Field     | Type    | Description                          |
| --------- | ------- | ------------------------------------ |
| `id`      | String  | Unique node identifier (hash-based)  |
| `type`    | Char    | `'d'` (directory) or `'f'` (file)    |
| `name`    | String  | Base name of file/directory          |
| `abs_path`| String  | Absolute file system path            |
| `size`    | Integer | File size in bytes (`null` for dirs) |

**Edges** (`*_edges.csv`):

| Field      | Type    | Description                |
| ---------- | ------- | -------------------------- |
| `id`       | String  | Unique edge identifier     |
| `source`   | String  | Parent node ID             |
| `target`   | String  | Child node ID              |
| `relation` | String  | Always `'contains'`        |

### Python AST Graph

**Nodes** (`*_nodes.csv`):

| Field           | Type    | Description                              |
| --------------- | ------- | ---------------------------------------- |
| `id`            | String  | Unique symbol identifier                 |
| `kind`          | String  | `module`, `class`, `function`, `method`  |
| `name`          | String  | Symbol name (unqualified)                |
| `qualified_name`| String  | Full dotted path (e.g., `module.Class.method`) |
| `module_path`   | String  | File path relative to scan root          |
| `lineno`        | Integer | Starting line number (1-based)           |
| `end_lineno`    | Integer | Ending line number                       |
| `signature`     | String  | Function/method signature (best-effort)  |
| `doc`           | String  | First line of docstring (if present)     |

**Edges** (`*_edges.csv`):

| Field      | Type    | Description                         |
| ---------- | ------- | ----------------------------------- |
| `id`       | String  | Unique edge identifier              |
| `source`   | String  | Source node ID                      |
| `target`   | String  | Target node ID                      |
| `relation` | String  | Relationship type (see below)       |
| `lineno`   | Integer | Line where relationship occurs      |
| `end_lineno`| Integer | End line of relationship            |

**Relation Types:**

- **`contains`** — Parent symbol contains child (class → method, module → class)
- **`imports`** — Module imports a symbol
- **`calls`** — Function/method calls another
- **`inherits`** — Class inherits from base class
- **`references`** — Other semantic reference

---

## Use Cases

### 1. LLM-Based Code Understanding

Feed flat CSVs to Claude/GPT for code analysis without token bloat:

```python
nodes_csv, edges_csv = scan_project(root)
context = build_context_for_llm(nodes_csv, edges_csv)
response = llm.analyze(context)
```

### 2. Static Analysis & Code Quality

Use SQL/DuckDB for queries:

```sql
-- Find all functions with no docstring
SELECT name, qualified_name, module_path
FROM ast_nodes
WHERE kind = 'function' AND doc IS NULL;

-- Find unused classes (no incoming calls/references)
SELECT n.name
FROM ast_nodes n
LEFT JOIN ast_edges e ON n.id = e.target
WHERE n.kind = 'class' AND e.id IS NULL;
```

### 3. Refactoring & Architecture

Build dependency graphs, identify circular imports, plan migrations.

### 4. Embeddings & Search

Compute embeddings per node, build semantic search indexes.

### 5. Data Pipelines

Load into Pandas for custom analysis:

```python
import pandas as pd

nodes = pd.read_csv("ast_nodes.csv")
edges = pd.read_csv("ast_edges.csv")

# Classes per module
classes_per_module = nodes[nodes['kind'] == 'class'].groupby('module_path').size()
print(classes_per_module)
```

---

## Commands Reference

### `filescan scan`

Run filesystem and/or AST scan.

```bash
filescan scan <ROOT> [OPTIONS]
```

**Options:**

- `--ignore-file FILE` — Use custom ignore file
- `--ast` — Include Python AST scan (default: filesystem only)
- `--ast-only` — Skip filesystem, only scan AST
- `-o, --output PREFIX` — Output file prefix (default: `graph`)
- `--output-ast PREFIX` — Separate prefix for AST output

**Examples:**

```bash
# Filesystem only
filescan scan ./src -o results/fs

# Both filesystem and AST
filescan scan ./src --ast -o results/project

# Custom ignore file
filescan scan ./src --ast --ignore-file .scanignore -o results/custom
```

### `filescan watch`

Watch a project directory and auto-scan on Python file changes.

```bash
filescan watch <ROOT> [OPTIONS]
```

**Options:**

- `--ignore-file FILE` — Use custom ignore file
- `-o, --output PREFIX` — Output file prefix (default: `graph`)
- `--output-ast PREFIX` — Separate prefix for AST output
- `--debounce SECONDS` — Debounce interval (default: `0.5`)

**Example:**

```bash
# Watch for changes, rescan every 0.5 seconds
filescan watch ./src -o results/live --debounce 0.5
```

Press `Ctrl+C` to stop watching.

### `filescan search`

Search an existing AST graph with semantic context.

```bash
filescan search <ROOT> <QUERY> --nodes <FILE> --edges <FILE>
```

**Required:**

- `<ROOT>` — Project root (must match AST scan root)
- `<QUERY>` — Search query (symbol name)
- `--nodes FILE` — Path to AST nodes CSV
- `--edges FILE` — Path to AST edges CSV

**Example:**

```bash
filescan search ./src "MyClass" \
  --nodes graph_ast_nodes.csv \
  --edges graph_ast_edges.csv
```

**Output:**

Shows all occurrences with semantic context:
- Match type (definition, call, reference, import, inherit)
- File path and line number
- Source code context
- Definition source (if available)

### `filescan uml`

Build AST graph and export a Mermaid class diagram markdown file.

```bash
filescan uml <ROOT> [OPTIONS]
```

**Options:**

- `--ignore-file FILE` 鈥?Use custom ignore file
- `-o, --output FILE` 鈥?Output markdown path (default: `graph_uml.md`)
- `--show-private` 鈥?Include private methods in class diagrams
- `--module-path-filter TEXT` 鈥?Include only nodes whose `module_path` contains `TEXT`
- `--title TEXT` 鈥?Markdown title (default: `AST UML`)

**Example:**

```bash
filescan uml ./src -o results/uml.md --module-path-filter "core/"
```

---

## Development

### Project Structure

```
filescan/
├── src/filescan/
│   ├── __init__.py              # Public API
│   ├── base.py                  # ScannerBase (ID generation, ignore handling)
│   ├── scanner.py               # Filesystem scanner
│   ├── ast_scanner.py           # Python AST scanner (astroid)
│   ├── graph_builder.py         # Unified builder
│   ├── search_engine.py         # Hybrid search (ripgrep + AST)
│   ├── file_watcher.py          # File change watcher
│   ├── utils.py                 # Utilities
│   ├── commands/
│   │   └── cli.py               # CLI entry point
│   └── default.fscanignore      # Built-in ignore rules
├── tests/                        # Unit tests
├── examples/                     # Usage examples
└── pyproject.toml
```

### Running Tests

```bash
pytest tests/
```

### Running Examples

```bash
python examples/scan_self.py
python examples/search_self.py
python -m examples.watch_self
```

### Building & Publishing

```bash
# Build wheel
python -m build

# Upload to PyPI
python -m twine upload dist/*
```

---

## Comparison to Alternatives

| Feature | `filescan` | AST-only tools | Tree JSON | `ripgrep` |
| --- | --- | --- | --- | --- |
| Filesystem structure | ✅ | ❌ | ❌ | ❌ |
| Python AST | ✅ | ✅ | ❌ | ❌ |
| Flat graph design | ✅ | ❌ | ❌ | ❌ |
| CSV/SQL-friendly | ✅ | ❌ | ❌ | ✅ |
| Cross-file semantics | ✅ | ~Some | ❌ | ❌ |
| CLI + Library | ✅ | ~Some | ❌ | ❌ |
| LLM-optimized | ✅ | ❌ | ❌ | ❌ |

---

## Architecture Notes

### Deterministic IDs

All node and edge IDs are **generated deterministically** from content hashes. This ensures:

- ✅ Reproducible scans (same input → same IDs)
- ✅ Collision detection and handling
- ✅ Stable linking across multiple scans

### Two-Pass AST Scanning

1. **Pass 1 — Definitions:** Collect all module/class/function definitions across all Python files
2. **Pass 2 — Relationships:** Resolve cross-file imports, calls, inherits, and references

This ensures all semantic relationships are resolvable in a single pass.

### Hybrid Search

The search engine combines:

- **ripgrep** for fast text search
- **AST index** for semantic enrichment

Results are ranked by semantic priority (definition > call > reference > import).

---

## Performance

Typical scan times (on modern hardware):

| Target | Filesystem | AST | Combined |
| --- | --- | --- | --- |
| 1K files | ~50ms | ~200ms | ~250ms |
| 10K files | ~200ms | ~2s | ~2.2s |
| 100K files | ~2s | ~20s | ~22s |

`filescan` is designed for **sub-second iteration** during development via `watch` mode.

---

## Limitations & Known Issues

- AST signatures are best-effort (lambda functions, comprehensions may be incomplete)
- Dynamically resolved imports (e.g., `__import__`, exec) are not captured
- Relationship extraction depends on static analysis (no runtime tracing)
- Search is file-relative; cross-filesystem projects need unified root

---

## Contributing

Contributions welcome! Open issues or PRs on [GitHub](https://github.com/DreamSoul-AI/filescan).

---

## License

MIT License — see [LICENSE](LICENSE) file.

---

## Support

- 📖 **Documentation:** See this README and examples/
- 🐛 **Report Issues:** [GitHub Issues](https://github.com/DreamSoul-AI/filescan/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/DreamSoul-AI/filescan/discussions)

---

**Made with ❤️ by [DreamSoul](https://github.com/DreamSoul-AI)**

