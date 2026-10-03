from funmovie.magnet.crawler import start_server


def command_line_runner() -> None:
    """启动长期运行的 DHT 磁力链接采集服务（永久阻塞，直到进程被终止）。

    注意：`start_server()` 内部线程都是永久循环，调用后不会返回；aria2 下载
    （`magnet_to_torrent_aria2c`）和种子解析（`parse_torrent`）是各自独立的
    一次性批处理任务，不与本服务串联执行，需要单独按 README 里的用法运行
    （此前这里依次调用三者，但后两个调用在 `start_server()` 之后永远是
    不可达的死代码）。
    """
    start_server()


if __name__ == "__main__":
    command_line_runner()
