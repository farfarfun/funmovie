# funmovie

磁力链接（magnet）采集与下载辅助工具：从网站爬取磁力/迅雷链接、直接监听 BitTorrent DHT 网络嗅探 info_hash、把迅雷链接（`thunder://`）解码还原成磁力链接，统一存入本地 SQLite（可选 Redis），再通过 aria2c 的 JSON-RPC 接口把磁力链接转成种子下载，最后解析 `.torrent` 文件的元信息。

> 注意：包名/导入名是 `notemovie`（历史 `note*` 命名遗留，见 [NAMING.md](https://github.com/farfarfun/todo-list/blob/master/NAMING.md)），与仓库名 `funmovie` 不一致。经查 PyPI 上目前**没有**发布 `notemovie` 这个包（404），下面只给出源码安装方式。

## 安装

PyPI 上没有可用的发布包，需要从源码安装：

```bash
git clone https://github.com/farfarfun/funmovie.git
cd funmovie
pip install -e .
```

## 用法示例

### 1. 从网页爬取磁力链接

```python
from notemovie.library.get_magnet import get_magnet

get_magnet()  # 爬取 notemovie/library/get_magnet.py 里内置的站点，把新磁力链接 upsert 进本地 SQLite
```

### 2. 迅雷链接转磁力链接

```python
from notemovie.utils import thunder2magnet

magnet = thunder2magnet('thunder://QUFtYWduZXQ6P3h0PXVybjpidGloOjY5NjVhMWE4MDRjYTY4MGNjMjRhNmU5OTEwNDNhMzY5YjFhMDViNzlaWg==')
print(magnet)
```

### 3. 磁力链接存储

```python
from notemovie.database.job import add_magnet, get_magnets

add_magnet('magnet:?xt=urn:btih:xxxx')
print(get_magnets(size=10))
```

默认落地到 `notemovie/database/movieset.db`（SQLite）。`notemovie/database/core_redis.py` 里还提供了一个 `RedisClient`，可以选择把磁力链接存到 Redis 而不是 SQLite。

### 4. 磁力链接转种子下载（依赖本地 aria2c）

```bash
python -m notemovie.magnet.magnet_to_torrent_aria2c
```

需要本地跑一个开启了 RPC 的 aria2c（默认连接 `127.0.0.1:6800`），会从数据库里取出待下载的磁力链接，通过 `aria2.addUri` 提交下载任务。

### 5. 解析 .torrent 文件

```python
from notemovie.magnet.parse_torrent import ParserTorrent

info = ParserTorrent('/path/to/xxx.torrent')
print(info.get_filename())
```

## 已知局限（如实说明）

- `notemovie/magnet/crawler.py` 实现了一个简化版 DHT 爬虫（`DHTServer`），用于直接从 BT 网络里嗅探 info_hash；该文件顶层直接调用了 `start_server()`，`magnet_to_torrent_aria2c.py` 顶层也直接调用了 `magnet2torrent()` —— 这两个文件按脚本方式运行即可，但 `import` 它们会立刻触发网络/RPC 调用，不是纯粹的库代码，使用前请注意。
- 部分路径（如种子保存目录 `SAVE_PATH`）里硬编码了作者本机路径，实际使用需要自行修改。
- 爬取的目标站点、tracker 列表等均为历史遗留配置，可能已失效，需要自行更新维护。
