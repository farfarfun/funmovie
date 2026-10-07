import os
import sqlite3
from pathlib import Path
from typing import Any


def default_database_path() -> Path:
    """返回默认 SQLite 数据库路径，始终位于用户可写的数据目录。"""
    data_home = os.environ.get("XDG_DATA_HOME")
    base_dir = Path(data_home) if data_home else Path.home() / ".local" / "share"
    return base_dir / "funmovie" / "movieset.db"


class _SqliteTable:
    """项目内部使用的轻量 SQLite 表封装。"""

    def __init__(self, table_name: str, db_path: str | None = None) -> None:
        self.table_name = table_name
        self.db_path = (
            Path(db_path)
            if db_path is not None
            else Path(os.environ.get("FUNMOVIE_DB_PATH", default_database_path()))
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.columns: list[str] = []

    def execute(self, sql: str, parameters: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        cursor = self.conn.execute(sql, parameters)
        self.conn.commit()
        return cursor

    def insert(self, properties: dict[str, Any]) -> None:
        values = {key: properties[key] for key in self.columns if key in properties}
        if not values:
            raise ValueError("至少需要提供一个有效字段")
        keys = list(values)
        placeholders = ", ".join("?" for _ in keys)
        self.execute(
            f"insert or ignore into {self.table_name} ({', '.join(keys)}) values ({placeholders})",
            tuple(values[key] for key in keys),
        )

    def update(self, properties: dict[str, Any], condition: dict[str, Any]) -> None:
        values = {key: properties[key] for key in self.columns if key in properties}
        filters = {key: condition[key] for key in self.columns if key in condition}
        if not values or not filters:
            raise ValueError("更新字段和条件不能为空")
        assignments = ", ".join(f"{key} = ?" for key in values)
        predicates = " and ".join(f"{key} = ?" for key in filters)
        self.execute(
            f"update {self.table_name} set {assignments} where {predicates}",
            tuple(values.values()) + tuple(filters.values()),
        )

    def select(self, sql: str, parameters: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        return list(self.execute(sql, parameters))

    def close(self) -> None:
        self.conn.close()


class MovieManage(_SqliteTable):
    """管理 SQLite 中的电影记录。"""

    def __init__(self, table_name: str = "movies", db_path: str | None = None) -> None:
        """初始化电影表管理器，但不自动建表。

        :param table_name: 数据表名
        :param db_path: SQLite 文件路径；省略时使用 ``FUNMOVIE_DB_PATH``，再使用用户数据目录
        """
        super().__init__(db_path=db_path, table_name=table_name)
        self.columns = ["url", "name", "type", "source", "category", "describe", "size"]

    def create(self) -> None:
        """创建电影表（表已存在时不做修改）。"""
        self.execute(f"""
                create table if not exists {self.table_name} (
                url                 varchar(500)  primary key
               ,type                varchar(50)  DEFAULT ('thunder')
               ,source              varchar(500)  DEFAULT ('')
               ,category            varchar(500)  DEFAULT ('')
               ,describe            varchar(5000) DEFAULT ('')
               ,name                varchar(500)  DEFAULT ('')
               ,size                integer       DEFAULT (0)
        )
        """)

    def update(
        self, properties: dict[str, Any], condition: dict[str, Any] | None = None
    ) -> None:
        """更新电影记录，默认按 ``url`` 定位。

        :param properties: 要更新的字段
        :param condition: 筛选条件；省略时使用 properties 中的 url
        """
        condition = condition or {"url": properties["url"]}
        super().update(properties, condition=condition)


class MagnetManage(_SqliteTable):
    """管理 SQLite 中的磁力链接记录。"""

    def __init__(self, table_name: str = "magnet", db_path: str | None = None) -> None:
        """初始化磁力链接表管理器，但不自动建表。

        :param table_name: 数据表名
        :param db_path: SQLite 文件路径；省略时使用 ``FUNMOVIE_DB_PATH``，再使用用户数据目录
        """
        super().__init__(db_path=db_path, table_name=table_name)
        self.columns = ["magnet", "status"]

    def create(self) -> None:
        """创建磁力链接表（表已存在时不做修改）。"""
        self.execute(f"""
                create table if not exists {self.table_name} (
                magnet              varchar(500)  primary key
               ,status              integer       DEFAULT (0)
        )
        """)

    def update(
        self, properties: dict[str, Any], condition: dict[str, Any] | None = None
    ) -> None:
        """更新磁力链接，默认按 ``magnet`` 定位。

        :param properties: 要更新的字段
        :param condition: 筛选条件；省略时使用 properties 中的 magnet
        """
        condition = condition or {"magnet": properties["magnet"]}
        super().update(properties, condition=condition)

    def get_magnets(self, size: int = 100) -> list[str]:
        """查询待处理的磁力链接。

        :param size: 最多返回条数
        :return: 磁力链接字符串列表
        """
        rows = self.select(
            f"select magnet from {self.table_name} where status = 0 limit ?", (size,)
        )
        return [str(row[0]) for row in rows]
