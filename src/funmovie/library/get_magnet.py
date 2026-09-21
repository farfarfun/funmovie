import requests
from bs4 import BeautifulSoup
from farlog import getLogger
from tqdm import tqdm

from funmovie.database.job import add_magnet
from funmovie.utils import thunder2magnet

logger = getLogger(__name__)


def web1(index_start: int = 90, index_end: int = 110) -> None:
    """
    爬取 mzzfree.com 站点列表页中的磁力/迅雷链接并写入本地存储

    :param index_start: 起始 itemid（含）
    :param index_end: 结束 itemid（不含）
    """

    def url2movie(url: str) -> None:
        try:
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            logger.error("抓取页面失败: url=%s, error=%s", url, e)
            return

        for item in soup.find_all("a"):
            if "href" not in item.attrs:
                continue

            href = item["href"]
            if href.startswith("http") or href.startswith("java"):
                continue
            elif href.startswith("magnet"):
                add_magnet(href)
            elif href.startswith("thunder"):
                href = thunder2magnet(href)
                add_magnet(href)

    for i in tqdm(range(index_start, index_end)):
        url = f"http://www.mzzfree.com/news/show.php?itemid={i}"
        url2movie(url)


def get_magnet() -> None:
    """采集内置站点（mzzfree.com）里的新磁力链接并 upsert 进本地存储"""
    web1()
