import base64
import binascii

from farlog import getLogger

logger = getLogger(__name__)


def thunder2url(url: str) -> str:
    """
    把迅雷链接（thunder://）解码还原成原始链接（通常是磁力链接）

    :param url: 迅雷链接，非 thunder:// 前缀时原样返回
    :return: 解码后的原始链接；解码失败时返回原始 url 并记录错误日志
    """
    url = str(url)
    if "thunder://" not in url:
        return url

    raw = url.replace("thunder://", "")
    try:
        decoded = base64.b64decode(raw)
        text = decoded.decode("gbk")
        return text[2 : len(text) - 2]
    except (binascii.Error, UnicodeDecodeError) as e:
        logger.error("解码迅雷链接失败: url=%s, error=%s", url, e)
        return url


def thunder2magnet(url: str) -> str:
    """
    把迅雷链接转换成磁力链接，若解码结果不是磁力链接则返回空字符串

    :param url: 迅雷链接
    :return: 磁力链接，不是磁力链接时返回空字符串
    """
    url = thunder2url(url)
    if url.startswith("magnet"):
        return url
    else:
        return ""
