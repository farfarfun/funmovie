import argparse
import json
import os
import sys
from collections.abc import Iterator
from http.client import HTTPConnection

from farlog import getLogger

from funmovie.database.job import get_magnets as _get_magnets

logger = getLogger(__name__)


class Aria2RpcError(RuntimeError):
    """aria2 JSON-RPC 返回了 error 字段时抛出。"""


SAVE_PATH = os.environ.get(
    "FUNMOVIE_SAVE_PATH", os.path.expanduser("~/.cache/funmovie/torrents")
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


def exec_rpc(magnet: str, save_path: str | os.PathLike[str] = SAVE_PATH) -> None:
    """
    通过 aria2c 的 JSON-RPC 接口提交磁力下载任务，减少线程资源占用。详见
    https://aria2.github.io/manual/en/html/aria2c.html?highlight=enable%20rpc#aria2.addUri

    :param magnet: 磁力链接
    :param save_path: 种子保存目录
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
                "dir": os.fspath(save_path),
            },
        ],
    }
    conn.request(
        "POST", "/jsonrpc", json.dumps(req), {"Content-Type": "application/json"}
    )

    res = json.loads(conn.getresponse().read())
    if "error" in res:
        logger.error(
            "aria2c 提交下载任务失败: magnet={}, error={}", magnet, res["error"]
        )
        raise Aria2RpcError(f"magnet={magnet}, error={res['error']}")


def magnet2torrent(save_path: str | os.PathLike[str] = SAVE_PATH) -> int:
    """把待下载的磁力链接逐个提交给 aria2c。单个链接提交失败不中断其余链接。

    :param save_path: 种子保存目录
    :return: 提交失败的磁力链接数量
    """
    failures = 0
    for magnet in get_magnets():
        try:
            exec_rpc(magnet, save_path)
        except Aria2RpcError:
            failures += 1
    return failures


def main() -> None:
    """解析命令行参数并提交 aria2 下载任务；只要有任务提交失败就以非 0 退出。"""
    parser = argparse.ArgumentParser(description="把数据库中的磁力链接提交给 aria2c")
    parser.add_argument(
        "--save-path",
        default=SAVE_PATH,
        help="种子保存目录（默认读取 FUNMOVIE_SAVE_PATH）",
    )
    args = parser.parse_args()
    failures = magnet2torrent(args.save_path)
    if failures:
        logger.error("本次共有 {} 个磁力链接提交 aria2 失败", failures)
        sys.exit(1)


if __name__ == "__main__":
    main()
