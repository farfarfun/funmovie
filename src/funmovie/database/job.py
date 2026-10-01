from funmovie.database.core import MagnetManage, MovieManage

manage: MovieManage | None = None
magnet: MagnetManage | None = None


def initialize(db_path: str | None = None) -> None:
    """显式初始化电影和磁力链接数据表。"""
    global manage, magnet
    manage = MovieManage(db_path=db_path)
    manage.create()
    magnet = MagnetManage(db_path=db_path)
    magnet.create()


def _magnet_manager() -> MagnetManage:
    if magnet is None:
        initialize()
    assert magnet is not None
    return magnet


def add_magnet(magnet_str: str) -> None:
    """
    将磁力链接写入本地存储，非 magnet: 开头的字符串会被忽略

    :param magnet_str: 磁力链接
    """
    if magnet_str.startswith("magnet"):
        _magnet_manager().insert({"magnet": magnet_str})


def get_magnet() -> str:
    """
    取出一条待处理的磁力链接

    :return: 磁力链接字符串
    """
    return _magnet_manager().get_magnets(1)[0]


def get_magnets(size: int = 10, status: int = 0) -> list[str]:
    """
    批量取出待处理的磁力链接

    :param size: 最多返回条数
    :param status: 保留参数，当前实现固定按 status==0（待处理）查询
    :return: 磁力链接字符串列表
    """
    return _magnet_manager().get_magnets(size)


def update_status(magnet_link: str, status: int = 1) -> None:
    """
    更新磁力链接的处理状态

    :param magnet_link: 磁力链接
    :param status: 目标状态
    """
    _magnet_manager().update({"magnet": magnet_link, "status": status})
