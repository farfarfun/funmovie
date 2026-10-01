from funmovie.magnet.crawler import start_server
from funmovie.magnet.magnet_to_torrent_aria2c import magnet2torrent
from funmovie.magnet.parse_torrent import parse_torrent


def command_line_runner() -> None:
    """依次启动 DHT 服务、aria2 下载任务和种子解析任务。"""
    start_server()
    magnet2torrent()
    parse_torrent()


if __name__ == "__main__":
    start_server()
