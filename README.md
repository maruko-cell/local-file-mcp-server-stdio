# local-file-mcp-server-stdio

一个基于 **stdio** 的 MCP Server（Python），提供两个工具：

- `local_file_create_file`：新增/写入文件（支持创建父目录、可选覆盖、原子写入）
- `local_file_rename`：重命名/移动文件（支持创建父目录、可选覆盖）

## 安全策略

- 仅允许操作一个根目录：环境变量 `LOCAL_FILE_MCP_ROOT`
- 仅允许相对路径，且所有文件操作只能在 `LOCAL_FILE_MCP_ROOT` 配置的根目录下
- 日志输出到 stderr，stdout 仅用于协议通信

## 使用示例

### 1）在根目录下创建/写入文件

调用 `local_file_create_file`：

```json
{
  "path": "notes/hello.txt",
  "content": "你好，MCP！\n",
  "overwrite": false,
  "make_parents": true,
  "encoding": "utf-8"
}
```

说明：`overwrite=false` 且文件已存在会报错；`make_parents=true` 会自动创建父目录。

### 2）覆盖写入已存在文件

```json
{
  "path": "notes/hello.txt",
  "content": "覆盖写入内容\n",
  "overwrite": true
}
```

### 3）重命名/移动文件

调用 `local_file_rename`：

```json
{
  "from_path": "notes/hello.txt",
  "to_path": "notes/hello-renamed.txt",
  "overwrite": false,
  "make_parents": true
}
```

说明：源不存在或目标冲突会报错；`overwrite=true` 仅允许覆盖文件，不覆盖目录。

## 安装与启动（本地验证）

在该目录下执行：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
LOCAL_FILE_MCP_ROOT="$(pwd)" python -m local_file_mcp_server_stdio.server
```

## Cursor 配置（~/.cursor/mcp.json）

在 `mcpServers` 下新增一项（示例）：

```json
{
  "mcpServers": {
    "local-file": {
      "command": "/ABS/PATHTO/.venv/bin/python",
      "args": ["-m", "local_file_mcp_server_stdio.server"],
      "env": {
        "LOCAL_FILE_MCP_ROOT": "/ABS/PATH/TO/SAFE/ROOT"
      }
    }
  }
}
```

提示：

- `command` 建议填写你本机虚拟环境里的 Python 路径（上面用占位符 `/ABS/PATH/...` 表示）。
- 也可以直接使用脚本入口：`local-file-mcp-server-stdio`（见 `pyproject.toml` 的 `[project.scripts]`），但 Cursor 的 `command/args` 组合通常更直观可控。
