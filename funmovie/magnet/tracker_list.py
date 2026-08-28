import os

import requests


# requests.get('https://trackerslist.com/all.txt').text.split('\n')
def get_track(url):
    lines = requests.get(url).text.split('\n')
    lines = [line for line in lines if len(line) > 0]
    text = '\n'.join(lines)

    open('./tracks/{}'.format(os.path.basename(url)), 'w').write(text)
    print(','.join(lines))


for url in ('https://trackerslist.com/best.txt', 'https://trackerslist.com/all.txt'):
    get_track(url)
