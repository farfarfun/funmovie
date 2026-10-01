import os
from pathlib import Path

import requests
from farlog import getLogger

logger = getLogger(__name__)
DEFAULT_OUTPUT_DIR = Path(__file__).with_name("tracks")


# requests.get('https://trackerslist.com/all.txt').text.split('\n')
def get_track(
    url: str, output_dir: str | os.PathLike[str] = DEFAULT_OUTPUT_DIR
) -> list[str]:
    """下载 tracker 列表并保存到指定目录。

    :param url: tracker 列表地址
    :param output_dir: 输出目录，默认使用模块旁的 tracks 目录
    :return: 非空 tracker 地址列表
    """
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    lines = response.text.split("\n")
    lines = [line for line in lines if len(line) > 0]
    text = "\n".join(lines)

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / os.path.basename(url)).write_text(text, encoding="utf-8")
    return lines


if __name__ == "__main__":
    for url in ("https://trackerslist.com/best.txt", "https://trackerslist.com/all.txt"):
        logger.info("下载 tracker 列表成功: %s", ",".join(get_track(url)))
