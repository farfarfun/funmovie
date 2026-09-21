#!/usr/bin/env python

import redis

# redis key
REDIS_KEY = "magnets"
# redis 地址
REDIS_HOST = "localhost"
# redis 端口
REDIS_PORT = 6379
# redis 密码
REDIS_PASSWORD = None
# redis 连接池最大连接量
REDIS_MAX_CONNECTION = 20


class RedisClient:
    """基于 Redis Set 的磁力链接存储客户端，作为 SQLite 存储的可选替代"""

    def __init__(
        self,
        host: str = REDIS_HOST,
        port: int = REDIS_PORT,
        password: str = REDIS_PASSWORD,
    ):
        conn_pool = redis.ConnectionPool(
            host=host,
            port=port,
            password=password,
            max_connections=REDIS_MAX_CONNECTION,
        )
        self.redis = redis.Redis(connection_pool=conn_pool)

    def add_magnet(self, magnet: str) -> None:
        """
        新增磁力链接

        :param magnet: 磁力链接
        """
        self.redis.sadd(REDIS_KEY, magnet)

    def get_magnets(self, count: int = 128) -> list:
        """
        随机返回指定数量的磁力链接

        :param count: 返回数量
        :return: 磁力链接列表
        """
        return self.redis.srandmember(REDIS_KEY, count)
