# filescan

**filescan** is a lightweight Python tool for **scanning filesystem structures and Python ASTs** and exporting them as **flat, graph-style representations**.

Instead of nested trees, `filescan` produces **stable lists of nodes with parent pointers**, making the output:

* easy to post-process
* friendly for CSV / DataFrame / SQL pipelines
* efficient for LLM ingestion and summarization

`filescan` can operate at two levels:

* **filesystem structure** (directories & files)
* **Python semantic structure** (modules, classes, functions, methods)

Both use the same flat graph design and export formats.



## Features

### Filesystem scanning

* Recursive directory traversal
* Flat node list with explicit `parent_id`
* Deterministic ordering
* Optional `.gitignore`-style filtering
* CSV and JSON export

### Python AST scanning

* Module, class, function, and method detection
* Nested functions and classes supported
* Stable symbol IDs with parent relationships
* Best-effort function signature extraction
* First-line docstring capture

### General

* Shared schema + export model
* Same API for filesystem and AST scanners
* Usable as **both a library and a CLI**
* Designed for automation, data pipelines, and AI workflows



## Installation

```bash
pip install filescan
```

Or for development:

```bash
pip install -e .
```



## Quick start (CLI)

### Filesystem scan (default)

Scan the current directory and write a CSV:

```bash
filescan
```

Scan a specific directory:

```bash
filescan ./data
```

Export as JSON:

```bash
filescan ./data --format json
```

Specify output base path:

```bash
filescan ./data -o out/tree
```

This generates:

```text
out/
├── tree.csv
└── tree.json
```



### Python AST scan

Scan Python source files and extract symbols:

```bash
filescan ./src --ast
```

Export AST symbols as JSON:

```bash
filescan ./src --ast --format json
```

Custom output path:

```bash
filescan ./src --ast -o out/symbols
```

This generates:

```text
out/
├── symbols.csv
└── symbols.json
```



## Ignore rules (`.fscanignore`)

`filescan` supports **gitignore-style patterns** via `pathspec`.

### Default behavior

* If `--ignore-file` is provided → use it
* Otherwise, look for:

```text
./.fscanignore   (current working directory)
```

Ignore rules apply to:

* filesystem scanning
* AST scanning (Python files are skipped if ignored)

### Example `.fscanignore`

```gitignore
.git/
.idea/
build/
dist/
__pycache__/
*.pyc
```



## Output formats

Both filesystem and AST scans produce **flat graphs** with schema metadata.



### Filesystem schema

| Field       | Description                                 |
| -- | - |
| `id`        | Unique integer ID                           |
| `parent_id` | Parent node ID (`null` for root)            |
| `type`      | `'d'` = directory, `'f'` = file             |
| `name`      | Base name                                   |
| `size`      | File size in bytes (`null` for directories) |

#### CSV example

```csv
# id: Unique integer ID for this node
# parent_id: ID of parent node, or null for root
# type: Node type: 'd' = directory, 'f' = file
# name: Base name of the file or directory
# size: File size in bytes; null for directories
id,parent_id,type,name,size
0,,d,data,
1,0,f,example.txt,128
```



### Python AST schema

| Field         | Description                                |
| - |  |
| `id`          | Unique integer ID for this symbol          |
| `parent_id`   | Parent symbol ID (`null` for module)       |
| `kind`        | `module` | `class` | `function` | `method` |
| `name`        | Symbol name                                |
| `module_path` | File path relative to scan root            |
| `lineno`      | Starting line number (1-based)             |
| `signature`   | Function or method signature (best-effort) |
| `doc`         | First line of docstring, if any            |

Nested functions and classes are represented naturally via `parent_id`.



## Library usage

### Filesystem scanner

```python
from filescan import Scanner

scanner = Scanner(
    root="data",
    ignore_file=".fscanignore",
)

scanner.scan()
scanner.to_csv()    # -> ./data.csv
scanner.to_json()   # -> ./data.json
```



### Python AST scanner

```python
from filescan import AstScanner

scanner = AstScanner(
    root="src",
    ignore_file=".fscanignore",
    output="out/symbols",
)

scanner.scan()
scanner.to_csv()
scanner.to_json()
```



### Programmatic access

```python
nodes = scanner.scan()
print(len(nodes))

data = scanner.to_dict()
```



## Why `filescan`?

Most filesystem and code structures are represented as deeply nested trees. While human-readable, they are verbose, hard to query, and inefficient for large-scale processing.

`filescan` represents both **filesystems and codebases** as **flat graphs** because this format is:

* **Compact and token-efficient**
  Flat lists with numeric IDs consume far fewer tokens than recursive trees, making them ideal for LLM context windows.

* **Explicit and unambiguous**
  All relationships are encoded directly via `parent_id`.

* **Easy to process**
  Flat data works naturally with filtering, joins, grouping, and graph analysis.

This makes `filescan` especially suitable for:

* SQL / Pandas / DuckDB pipelines
* Static analysis and refactoring tools
* Graph-based code understanding
* **LLM-based reasoning and summarization of projects**

In short, `filescan` favors **machine-friendly structure over visual trees**, enabling scalable, AI-native workflows.



## Development

The project uses a `src/` layout.

Examples can be run without installation:

```bash
python examples/scan_data.py
```

Or as a module:

```bash
python -m examples.scan_data
```



## License

MIT License
