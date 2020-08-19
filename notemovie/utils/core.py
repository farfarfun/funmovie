import base64


def thunder2url(url):
    try:
        url = str(url)
        if "thunder://" not in url:
            return url

        url = url.replace('thunder://', '')
        url = base64.b64decode(url)
        url = url.decode('gbk')
        url = url[2:len(url) - 2]
    except Exception as e:
        print("{}-error-{}".format(url, e))

    return url


def thunder2magnet(url):
    url = thunder2url(url)
    if url.startswith('magnet'):
        return url
    else:
        return ''
