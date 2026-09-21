import os
from collections.abc import Iterator
from logging import Logger
from socket import inet_ntoa
from struct import unpack

from farlog import getLogger

# 每个节点长度
PER_NODE_LEN = 26
# 节点 id 长度
PER_NID_LEN = 20
# 节点 id 和 ip 长度
PER_NID_NIP_LEN = 24
# 构造邻居随机结点
NEIGHBOR_END = 14


def get_rand_id() -> bytes:
    """
    生成随机的节点 id，长度为 20 位

    :return: 20 字节的随机节点 id
    """
    return os.urandom(PER_NID_LEN)


def get_neighbor(target: bytes) -> bytes:
    """
    生成随机 target 周边节点 id，在 Kademlia 网络中，距离是通过异或(XOR)计算的，
    结果为无符号整数。distance(A, B) = |A xor B|，值越小表示越近。

    :param target: 节点 id
    :return: 与 target 前 14 字节相同、后 6 字节随机的邻居节点 id
    """
    return target[:NEIGHBOR_END] + get_rand_id()[NEIGHBOR_END:]


def get_nodes_info(nodes: bytes) -> Iterator[tuple[bytes, str, int]]:
    """
    解析 find_node 回复中 nodes 节点的信息

    :param nodes: 紧凑编码的节点列表字节串
    :return: (节点 id, ip, port) 三元组的迭代器；长度不是 26 的整数倍时返回空
    """
    length = len(nodes)
    # 每个节点单位长度为 26 为，node = node_id(20位) + node_ip(4位) + node_port(2位)
    if (length % PER_NODE_LEN) != 0:
        return

    for i in range(0, length, PER_NODE_LEN):
        nid = nodes[i : i + PER_NID_LEN]
        # 利用 inet_ntoa 可以返回节点 ip
        ip = inet_ntoa(nodes[i + PER_NID_LEN : i + PER_NID_NIP_LEN])
        # 解包返回节点端口
        port = unpack("!H", nodes[i + PER_NID_NIP_LEN : i + PER_NODE_LEN])[0]
        yield (nid, ip, port)


def get_logger(logger_name: str) -> Logger:
    """
    返回 farlog 日志实例

    :param logger_name: 日志名称
    :return: farlog 提供的 Logger 实例
    """
    return getLogger(logger_name)
