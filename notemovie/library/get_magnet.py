import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from notemovie.database.job import add_magnet
from notemovie.utils import thunder2magnet


def web1(index_start=90, index_end=110):
    """
    http://www.mzzfree.com/feed/
    :return:
    """

    def url2movie(url):
        try:
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'lxml')

            for item in soup.find_all('a'):
                if 'href' not in item.attrs:
                    continue

                href = item['href']
                if href.startswith('http') or href.startswith('java'):
                    continue
                elif href.startswith('magnet'):
                    add_magnet(href)
                elif href.startswith('thunder'):
                    href = thunder2magnet(href)
                    add_magnet(href)
                else:
                    # print(item)
                    pass
        except Exception as e:
            print("{}-error-{}".format(url, e))
            return

    for i in tqdm(range(index_start, index_end)):
        url = 'http://www.mzzfree.com/news/show.php?itemid={}'.format(i)
        url2movie(url)


def get_magnet():
    web1()
