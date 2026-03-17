# local-file-mcp-server-stdio

A **stdio**-based MCP Server (Python) that provides two tools:

- `local_file_create_file`: create/write a file (supports creating parent directories, optional overwrite, and atomic writes)
- `local_file_rename`: rename/move a file (supports creating parent directories and optional overwrite)

## Security policy

- Only operates under a single root directory: environment variable `LOCAL_FILE_MCP_ROOT`
- Only relative paths are allowed, and all file operations must stay under the root set by `LOCAL_FILE_MCP_ROOT`
- Logs are written to stderr; stdout is reserved for protocol communication only

## Usage examples

### 1) Create/write a file under the root directory

Call `local_file_create_file`:

```json
{
  "path": "notes/hello.txt",
  "content": "你好，MCP！\n",
  "overwrite": false,
  "make_parents": true,
  "encoding": "utf-8"
}
```

Note: If `overwrite=false` and the file already exists, it will error; `make_parents=true` will automatically create parent directories.

### 2) Overwrite an existing file

```json
{
  "path": "notes/hello.txt",
  "content": "覆盖写入内容\n",
  "overwrite": true
}
```

### 3) Rename/move a file

Call `local_file_rename`:

```json
{
  "from_path": "notes/hello.txt",
  "to_path": "notes/hello-renamed.txt",
  "overwrite": false,
  "make_parents": true
}
```

Note: It will error if the source does not exist or the target conflicts; `overwrite=true` can only overwrite files, not directories.

## Install & run (local verification)

Run in this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
LOCAL_FILE_MCP_ROOT="$(pwd)" python -m local_file_mcp_server_stdio.server
```

## Cursor configuration (`~/.cursor/mcp.json`)

Add an entry under `mcpServers` (example):

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

Tips:

- `command` is recommended to point to the Python executable inside your virtual environment (placeholders shown as `/ABS/PATH/...`).
- You can also use the script entrypoint `local-file-mcp-server-stdio` (see `[project.scripts]` in `pyproject.toml`), but the `command/args` form in Cursor is often more explicit and controllable.

