import os
from pathlib import Path

import requests


# requests.get('https://trackerslist.com/all.txt').text.split('\n')
def get_track(url: str, output_dir: str | os.PathLike[str] = "tracks") -> list[str]:
    """下载 tracker 列表并保存到指定目录，返回有效地址。"""
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
        print(",".join(get_track(url)))
