import codecs
import os
from pprint import pprint

from bencoder import bdecode

TORRENT_SAVE_PATH = "torrents"


class ParserTorrent:
    """解析 .torrent 文件的元信息（文件名、创建时间、创建者等）"""

    def __init__(self, torrent: str):
        self.meta_info = self.get_meta_info(torrent)

    @staticmethod
    def get_meta_info(torrent: str) -> dict:
        """
        读取并解码 .torrent 文件，返回解码后的 meta info 字典

        :param torrent: .torrent 文件路径
        :return: bencode 解码后的元信息字典
        """
        with open(torrent, "rb") as f:
            return bdecode(f.read())

    def is_files(self) -> bool:
        """
        判断种子文件为单文件或者多文件

        :return: 多文件种子返回 True，单文件返回 False
        """
        return b"files" in self.meta_info[b"info"]

    def get_creation_date(self) -> int | None:
        """
        获取种子创建时间（Unix 时间戳）

        :return: 创建时间戳；种子未记录该字段时返回 None
        """
        if b"creation date" in self.meta_info:
            return self.meta_info[b"creation date"]
        return None

    def _get_single_filename(self) -> str:
        """
        获取单文件种子的文件名

        :return: 文件名
        """
        info = self.meta_info[b"info"]
        if b"name.utf-8" in info:
            filename = info[b"name.utf-8"]
        else:
            filename = info[b"name"]
        for c in filename:
            if c == "'":
                filename = filename.replace(c, "\\'")
        return filename.decode()

    def _get_multi_filename(self) -> list:
        """
        获取多文件种子里每个文件的信息（路径、大小等）

        :return: (字段名, 值) 二元组组成的列表；字节串字段无法按 utf-8 解码时，
            退化为十六进制字符串表示
        """
        files = self.meta_info[b"info"][b"files"]
        info = []
        for item in files:
            for k, v in item.items():
                if isinstance(v, list):
                    try:
                        v = [i.decode() for i in v]
                    except UnicodeDecodeError:
                        v = [codecs.getencoder("hex")(i)[0].decode() for i in v]
                elif isinstance(v, int):
                    v = round(v / 1024 / 1024, 2)
                else:
                    v = codecs.getencoder("hex")(v)[0].decode()
                info.append((k.decode(), v))
        return info

    def get_filename(self) -> str | list:
        """
        获取种子文件名：单文件返回文件名字符串，多文件返回文件信息列表

        :return: 单文件为文件名字符串，多文件为 `_get_multi_filename` 的结果
        """
        if self.is_files():
            return self._get_multi_filename()
        else:
            return self._get_single_filename()

    def get_createby(self) -> str | None:
        """
        获取种子创建者

        :return: 创建者字符串；种子未记录该字段时返回 None
        """
        if b"created by" in self.meta_info:
            return self.meta_info[b"created by"]
        return None


def parse_torrent() -> None:
    """遍历 `TORRENT_SAVE_PATH` 目录下的全部 .torrent 文件，打印其文件名信息"""
    for _, _, files in os.walk(TORRENT_SAVE_PATH):
        for file in files:
            info = ParserTorrent(os.path.join(TORRENT_SAVE_PATH, file))
            print(TORRENT_SAVE_PATH, file)
            pprint(info.get_filename())
            print()
