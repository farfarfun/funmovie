import json
from collections.abc import Iterator
from http.client import HTTPConnection

from farlog import getLogger

from funmovie.database.job import get_magnets as _get_magnets

logger = getLogger(__name__)

# 种子保存目录，实际使用需按本机环境修改
SAVE_PATH = (
    "/Users/liangtaoniu/workspace/MyDiary/notechats/funmovie/funmovie/magnet/torrents"
)
STOP_TIMEOUT = 60
MAX_CONCURRENT = 16
MAX_MAGNETS = 10

ARIA2RPC_ADDR = "127.0.0.1"
ARIA2RPC_PORT = 6800


def get_magnets() -> Iterator[str]:
    """
    从本地存储中取出待下载的磁力链接

    :return: 磁力链接字符串的迭代器
    """
    mgs = _get_magnets(MAX_MAGNETS)
    for m in mgs:
        yield m


def exec_rpc(magnet: str) -> None:
    """
    通过 aria2c 的 JSON-RPC 接口提交磁力下载任务，减少线程资源占用。详见
    https://aria2.github.io/manual/en/html/aria2c.html?highlight=enable%20rpc#aria2.addUri

    :param magnet: 磁力链接
    """
    conn = HTTPConnection(ARIA2RPC_ADDR, ARIA2RPC_PORT)
    req = {
        "jsonrpc": "2.0",
        "id": "magnet",
        "method": "aria2.addUri",
        "params": [
            [magnet],
            {
                "bt-stop-timeout": str(STOP_TIMEOUT),
                "max-concurrent-downloads": str(MAX_CONCURRENT),
                "listen-port": "6881",
                "dir": SAVE_PATH,
            },
        ],
    }
    conn.request(
        "POST", "/jsonrpc", json.dumps(req), {"Content-Type": "application/json"}
    )

    res = json.loads(conn.getresponse().read())
    if "error" in res:
        logger.error(
            "aria2c 提交下载任务失败: magnet=%s, error=%s", magnet, res["error"]
        )


def magnet2torrent() -> None:
    """把本地存储中待下载的磁力链接逐个提交给 aria2c 转成种子下载任务"""
    for magnet in get_magnets():
        exec_rpc(magnet)


if __name__ == "__main__":
    magnet2torrent()
