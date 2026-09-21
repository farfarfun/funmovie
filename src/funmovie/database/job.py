from funmovie.database.core import MagnetManage, MovieManage

manage = MovieManage()
manage.create()
magnet = MagnetManage()
magnet.create()


def add_magnet(magnet_str: str) -> None:
    """
    将磁力链接写入本地存储，非 magnet: 开头的字符串会被忽略

    :param magnet_str: 磁力链接
    """
    if magnet_str.startswith("magnet"):
        magnet.insert({"magnet": magnet_str})


def get_magnet() -> str:
    """
    取出一条待处理的磁力链接

    :return: 磁力链接字符串
    """
    return magnet.get_magnets(1)[0]


def get_magnets(size: int = 10, status: int = 0) -> list:
    """
    批量取出待处理的磁力链接

    :param size: 最多返回条数
    :param status: 保留参数，当前实现固定按 status==0（待处理）查询
    :return: 磁力链接字符串列表
    """
    return magnet.get_magnets(size)


def update_status(magnet_link: str, status: int = 1) -> None:
    """
    更新磁力链接的处理状态

    :param magnet_link: 磁力链接
    :param status: 目标状态
    """
    magnet.update({"magnet": magnet_link, "status": status})
