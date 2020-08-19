from notemovie.magnet.crawler import start_server
from notemovie.magnet.magnet_to_torrent_aria2c import magnet2torrent
from notemovie.magnet.parse_torrent import parse_torrent


def command_line_runner():
    """
    执行命令行操作
    """
    start_server()
    magnet2torrent()
    parse_torrent()


if __name__ == "__main__":
    start_server()
