# filescan

**filescan** 是一个轻量级 Python 工具，用于扫描：

* 📁 **文件系统结构**
* 🧠 **Python 语义结构（AST）**

并将它们导出为**扁平图结构（Flat Graph）表示**。

不同于传统的嵌套树结构，`filescan` 生成的是稳定的 **节点 + 边 列表**，使输出结果：

* 易于查询
* 适用于 CSV / SQL / Pandas 等数据处理流程
* 更高效地用于 LLM 输入
* 适合图分析和代码理解

文件系统扫描与 AST 扫描采用统一的图模型设计。

---

# 为什么使用扁平图结构？

传统树结构：

* 层级嵌套深
* 冗长
* 难以筛选
* 不适合大规模处理
* 在 LLM 中 token 消耗高

`filescan` 使用扁平图模型：

```
nodes.csv
edges.csv
```

关系通过 ID 显式表示，而不是嵌套结构。

优势：

* 机器友好
* 易查询
* Token 高效
* 天然适合 AI 工作流

---

# 功能特性

## 📁 文件系统扫描

* 递归遍历目录
* 稳定、确定性的输出顺序
* 显式父子关系边
* 支持 `.gitignore` 风格过滤
* CSV / JSON 导出
* 稳定的数值 ID

---

## 🧠 Python AST 扫描

* 模块检测
* 类检测
* 函数与方法检测
* 支持嵌套定义
* 函数签名提取（尽力而为）
* 文档字符串首行提取
* 跨文件语义关系：

  * `contains`（包含）
  * `imports`（导入）
  * `calls`（调用）
  * `inherits`（继承）
  * `references`（引用）

---

## ⚙ 通用特性

* 统一的图结构 schema
* 文件系统与 AST 扫描 API 一致
* 支持 CLI 和库调用
* 专为自动化与 AI 工作流设计

---

# 安装

```bash
pip install filescan
```

开发模式安装：

```bash
pip install -e .
```

---

# 快速开始（CLI）

## 文件系统扫描（默认）

扫描当前目录：

```bash
filescan
```

扫描指定目录：

```bash
filescan ./data
```

导出为 JSON：

```bash
filescan ./data --format json
```

指定输出路径：

```bash
filescan ./data -o out/tree
```

输出结果：

```
out/
├── tree_nodes.csv
└── tree_edges.csv
```

---

## Python AST 扫描

扫描 Python 源码：

```bash
filescan ./src --ast
```

导出为 JSON：

```bash
filescan ./src --ast --format json
```

指定输出路径：

```bash
filescan ./src --ast -o out/symbols
```

输出结果：

```
out/
├── symbols_nodes.csv
└── symbols_edges.csv
```

---

# 忽略规则（`.fscanignore`）

`filescan` 使用 `pathspec` 支持 **gitignore 风格规则**。

### 规则解析顺序：

1. 如果指定 `--ignore-file`，优先使用
2. 当前工作目录下的 `./.fscanignore`
3. 内置默认忽略规则

忽略规则适用于：

* 文件系统扫描
* AST 扫描（被忽略的 Python 文件不会被解析）

### 示例 `.fscanignore`

```gitignore
.git/
.idea/
build/
dist/
__pycache__/
*.pyc
```

---

# 输出格式

两种扫描都会生成：

* `*_nodes.csv`
* `*_edges.csv`
* 可选 JSON

CSV 文件中包含 schema 元数据注释。

---

# 文件系统图 Schema

## 节点（Nodes）

| 字段     | 描述                    |
| ------ | --------------------- |
| `id`   | 唯一整数 ID               |
| `type` | `'d'` = 目录，`'f'` = 文件 |
| `name` | 文件或目录名称               |
| `size` | 文件大小（目录为 `null`）      |

## 边（Edges）

| 字段         | 描述             |
| ---------- | -------------- |
| `id`       | 唯一边 ID         |
| `source`   | 父节点 ID         |
| `target`   | 子节点 ID         |
| `relation` | 固定为 `contains` |

---

# Python AST 图 Schema

## 节点（Nodes）

| 字段               | 描述                                      |
| ---------------- | --------------------------------------- |
| `id`             | 唯一符号 ID                                 |
| `kind`           | `module`, `class`, `function`, `method` |
| `name`           | 符号名称                                    |
| `qualified_name` | 完整限定名                                   |
| `module_path`    | 相对于扫描根目录的文件路径                           |
| `lineno`         | 起始行号（1-based）                           |
| `end_lineno`     | 结束行号                                    |
| `signature`      | 函数签名                                    |
| `doc`            | 文档字符串首行                                 |

## 边（Edges）

| 关系           | 含义       |
| ------------ | -------- |
| `contains`   | 父符号包含子符号 |
| `imports`    | 模块导入符号   |
| `calls`      | 函数调用符号   |
| `inherits`   | 类继承关系    |
| `references` | 符号引用关系   |

---

# 库方式使用

## 文件系统扫描

```python
from filescan import Scanner

scanner = Scanner(root="data")
scanner.scan()
scanner.to_csv()
scanner.to_json()
```

---

## Python AST 扫描

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

---

## 程序化访问

```python
nodes = scanner.scan()

print(len(nodes))
print(nodes[0])
```

---

# 面向 AI 与数据管线设计

`filescan` 特别适用于：

* LLM 代码理解
* Token 高效的项目摘要
* 静态分析
* 代码图生成
* SQL / Pandas / DuckDB 数据处理
* 重构工具
* 跨文件语义分析

相比嵌套 JSON 树结构，扁平图结构在以下场景中更高效：

* 输入到 LLM
* 关系查询与 join
* 图算法处理
* 构建代码嵌入向量

`filescan` 的核心理念是：

> 用机器友好的图结构替代人类可视化树结构，构建可扩展的 AI 原生代码分析工作流。

---

# 开发

项目采用 `src/` 结构。

运行示例：

```bash
python examples/scan_data.py
```

或：

```bash
python -m examples.scan_data
```

---

# License

MIT License

