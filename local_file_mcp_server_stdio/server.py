import os
import sys
import time
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP


def _log(message: str) -> None:
    """
    将服务运行日志输出到标准错误，便于在 MCP Host 中区分来源与排查问题。

    入参说明：
    - message（str）：要输出的日志内容。

    返回值说明：
    - 无返回值。
    """
    sys.stderr.write(f"[local-file-mcp-stdio] {message}\n")
    sys.stderr.flush()


def _root_dir() -> Path:
    """
    获取并规范化本服务允许访问的根目录（用于后续路径安全校验）。

    入参说明：
    - 无入参。

    返回值说明：
    - Path：根目录的绝对路径（已展开用户目录并 resolve）。

    关键逻辑备注：
    - 优先读取环境变量 LOCAL_FILE_MCP_ROOT；未设置时使用当前工作目录。
    """
    root = os.environ.get("LOCAL_FILE_MCP_ROOT") or os.getcwd()
    return Path(root).expanduser().resolve()


def _resolve_safe(root: Path, rel_path: str) -> Path:
    """
    将相对路径解析为根目录下的安全绝对路径，禁止绝对路径与越权跳出根目录。

    入参说明：
    - root（Path）：允许访问的根目录绝对路径。
    - rel_path（str）：待解析的相对路径字符串。

    返回值说明：
    - Path：解析后的目标文件/目录绝对路径（位于 root 之下）。

    关键逻辑备注：
    - 拒绝空路径与非字符串；
    - 拒绝绝对路径；
    - 通过 `resolve()` + `relative_to(root)` 校验是否发生目录穿越。
    """
    if not isinstance(rel_path, str) or not rel_path.strip():
        raise ValueError("path 不能为空")

    p = Path(rel_path)
    if p.is_absolute():
        raise ValueError("只允许相对路径")

    full = (root / p).resolve()
    try:
        full.relative_to(root)
    except Exception:
        raise ValueError("非法路径：不允许跳出根目录")

    return full


def _atomic_write_text(path: Path, content: str, *, encoding: str) -> int:
    """
    以尽量原子的方式写入文本内容到指定路径，避免写入过程中产生半文件。

    入参说明：
    - path（Path）：目标文件绝对路径。
    - content（str）：要写入的文本内容（None 会被当作空字符串）。
    - encoding（str）：文本编码（关键字参数）。

    返回值说明：
    - int：实际写入的字节数。

    关键逻辑备注：
    - 先在同目录写入临时文件，再通过 replace 覆盖目标文件，以提升原子性与跨平台兼容性。
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    data = (content or "").encode(encoding)

    # 同目录临时文件，再 replace，尽量原子
    tmp_name = f".{path.name}.tmp.{os.getpid()}.{int(time.time() * 1000)}"
    tmp_path = path.with_name(tmp_name)
    tmp_path.write_bytes(data)
    tmp_path.replace(path)
    return len(data)


mcp = FastMCP("local-file-mcp-server-stdio")


@mcp.tool()
def local_file_create_file(
    path: str,
    content: Optional[str] = "",
    overwrite: bool = False,
    make_parents: bool = True,
    encoding: str = "utf-8",
):
    """
    在受控根目录（LOCAL_FILE_MCP_ROOT）下新增或写入文件，仅允许相对路径以确保安全。

    入参说明：
    - path（str）：相对根目录的文件路径（不允许绝对路径）。
    - content（Optional[str]）：写入内容；None 视为 ""。
    - overwrite（bool）：目标已存在时是否覆盖。
    - make_parents（bool）：是否自动创建父目录。
    - encoding（str）：写入文本使用的编码。

    返回值说明：
    - dict：包含 ok、path、bytes_written、created 等字段的结果对象。

    关键逻辑备注：
    - 通过 `_resolve_safe` 防止目录穿越；
    - 写入使用 `_atomic_write_text`，尽量保证覆盖写入的原子性。
    """
    root = _root_dir()
    full = _resolve_safe(root, path)

    if make_parents:
        full.parent.mkdir(parents=True, exist_ok=True)

    existed = full.exists()
    if existed and not overwrite:
        raise ValueError("文件已存在（overwrite=false）")

    bytes_written = _atomic_write_text(full, content or "", encoding=encoding)
    rel = str(full.relative_to(root))
    _log(f"create_file path={rel} existed={existed} overwrite={overwrite} bytes={bytes_written}")

    return {
        "ok": True,
        "path": rel,
        "bytes_written": bytes_written,
        "created": (not existed),
    }


@mcp.tool()
def local_file_rename(
    from_path: str,
    to_path: str,
    overwrite: bool = False,
    make_parents: bool = True,
):
    """
    在受控根目录（LOCAL_FILE_MCP_ROOT）下重命名/移动文件，仅允许相对路径以确保安全。

    入参说明：
    - from_path（str）：源文件相对路径。
    - to_path（str）：目标文件相对路径。
    - overwrite（bool）：目标已存在时是否覆盖（仅允许覆盖文件，不允许覆盖目录）。
    - make_parents（bool）：是否自动创建目标父目录。

    返回值说明：
    - dict：包含 ok、from_path、to_path 等字段的结果对象。

    关键逻辑备注：
    - 通过 `_resolve_safe` 校验源/目标都在根目录下；
    - overwrite=true 时会先删除目标文件，再执行 replace；
    - 使用 replace 实现“移动/重命名”。
    """
    root = _root_dir()
    src = _resolve_safe(root, from_path)
    dst = _resolve_safe(root, to_path)

    if not src.exists():
        raise ValueError("源文件不存在")

    if make_parents:
        dst.parent.mkdir(parents=True, exist_ok=True)

    if dst.exists():
        if not overwrite:
            raise ValueError("目标已存在（overwrite=false）")
        if dst.is_dir():
            raise ValueError("目标路径是目录，无法覆盖")
        dst.unlink()

    src.replace(dst)
    _log(f"rename from={from_path} to={to_path} overwrite={overwrite}")

    return {
        "ok": True,
        "from_path": str(Path(from_path)),
        "to_path": str(Path(to_path)),
    }


def main() -> None:
    """
    启动 MCP 服务并进入事件循环，作为本模块的命令行入口。

    入参说明：
    - 无入参。

    返回值说明：
    - 无返回值。

    关键逻辑备注：
    - 启动前会输出 root 目录日志，便于确认 LOCAL_FILE_MCP_ROOT 是否生效。
    """
    root = _root_dir()
    _log(f"starting (root={root})")
    mcp.run()


if __name__ == "__main__":
    main()

