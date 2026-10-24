"""独立测试包的资源标记与用户数据目录。"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

#: 数据目录在用户目录下的名字。这个 fork 把应用改名为 Videodrome，数据目录也跟着
#: 改名：换名字不是为了甩掉历史，而是为了让用户在活动监视器里看到的名字和应用
#: 对得上。
DATA_DIR_NAME = "Videodrome"

#: 改名前的数据目录。还在就搬过去，搬不动就留在原地并说明，别让用户以为自己
#: 的馆藏没了。
LEGACY_DATA_DIR_NAME = "Peach"


def standalone() -> bool:
    return bool(getattr(sys, "frozen", False) and
                (Path(getattr(sys, "_MEIPASS", "")) / "standalone.txt").is_file())


def _base(environ: dict[str, str]) -> Path:
    if sys.platform == "win32":
        return Path(environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return Path.home() / "Library" / "Application Support"


def user_data_root(environ: dict[str, str]) -> Path:
    return _base(environ) / DATA_DIR_NAME / "peach-data"


def legacy_user_data_root(environ: dict[str, str]) -> Path:
    """改名前的数据目录：还在就说明这台机器升级过。"""
    return _base(environ) / LEGACY_DATA_DIR_NAME / "peach-data"


def migrate_legacy_data_root(environ: dict[str, str]) -> tuple[Path, Path | None]:
    """把旧的数据目录搬到新的名下。

    搬之前先确认新的不在：两个目录都有数据时不动任何东西，让用户自己决定，
    免得覆盖掉哪一边。搬不成功就留在原地，程序照常用新路径，只是数据还得从
    旧目录找。

    返回 (新目录, 搬过来的旧目录或 None)。
    """
    new = user_data_root(environ)
    old = legacy_user_data_root(environ)
    if not old.is_dir() or new.exists():
        return new, None
    try:
        new.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(old), str(new))
    except OSError:
        return new, None
    return new, old
