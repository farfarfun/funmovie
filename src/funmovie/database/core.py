import os

from funtool.database import SqliteTable


class MovieManage(SqliteTable):
    def __init__(self, table_name="movies", db_path=None, *args, **kwargs):
        if db_path is None:
            db_path = os.path.abspath(os.path.dirname(__file__)) + "/movieset.db"

        super().__init__(db_path=db_path, table_name=table_name, *args, **kwargs)
        self.columns = ["url", "name", "type", "source", "category", "describe", "size"]

    def create(self):
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

    def update(self, properties: dict, condition: dict = None):
        condition = condition or {"url": properties["url"]}
        super().update(properties, condition=condition)


class MagnetManage(SqliteTable):
    def __init__(self, table_name="magnet", db_path=None, *args, **kwargs):
        if db_path is None:
            db_path = os.path.abspath(os.path.dirname(__file__)) + "/movieset.db"

        super().__init__(db_path=db_path, table_name=table_name, *args, **kwargs)
        self.columns = ["magnet", "status"]

    def create(self):
        self.execute(f"""
                create table if not exists {self.table_name} (
                magnet              varchar(500)  primary key 
               ,status              integer       DEFAULT (0)
        )
        """)

    def update(self, properties: dict, condition: dict = None):
        condition = condition or {"magnet": properties["magnet"]}
        super().update(properties, condition=condition)

    def get_magnets(self, size: int = 100) -> list:
        """
        查询状态为待处理（status==0）的磁力链接

        :param size: 最多返回条数
        :return: 磁力链接字符串列表
        """
        sql = f"select magnet from {self.table_name} where status==0 limit {size}"
        return [line[0] for line in self.select(sql)]
