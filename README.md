# funmovie

磁力链接（magnet）采集与下载辅助工具：从网站爬取磁力/迅雷链接、直接监听 BitTorrent DHT 网络嗅探 info_hash、把迅雷链接（`thunder://`）解码还原成磁力链接，统一存入本地 SQLite（可选 Redis），再通过 aria2c 的 JSON-RPC 接口把磁力链接转成种子下载，最后解析 `.torrent` 文件的元信息。

包名/导入名与仓库名一致，均为 `funmovie`。经查 PyPI 上目前**没有**发布 `funmovie` 这个包（404）；开发请从源码运行，生产请自行构建并安装 wheel。

## 源码开发

克隆源码后用 `uv` 建立开发环境：

```bash
git clone https://github.com/farfarfun/funmovie.git
cd funmovie
uv sync
```

也可使用 pip 进行 editable 安装：

```bash
pip install -e .
```

## 正式安装

在源码检出目录构建 wheel，并在目标运行环境安装它：

```bash
uv build
pip install dist/funmovie-0.0.5-py3-none-any.whl
```

## 用法示例

### 1. 从网页爬取磁力链接

```python
from funmovie.library.get_magnet import get_magnet

get_magnet()  # 爬取 funmovie/library/get_magnet.py 里内置的站点，把新磁力链接写入本地 SQLite
```

### 2. 迅雷链接转磁力链接

```python
from funmovie.utils import thunder2magnet

magnet = thunder2magnet(
    "thunder://QUFtYWduZXQ6P3h0PXVybjpidGloOjY5NjVhMWE4MDRjYTY4MGNjMjRhNmU5OTEwNDNhMzY5YjFhMDViNzlaWg=="
)
print(magnet)
```

### 3. 磁力链接存储

```python
from funmovie.database.job import add_magnet, get_magnets

add_magnet("magnet:?xt=urn:btih:xxxx")
print(get_magnets(size=10))
```

默认落地到 `$XDG_DATA_HOME/funmovie/movieset.db`（未设置时为 `~/.local/share/funmovie/movieset.db`）。可调用 `funmovie.database.job.initialize(db_path=...)` 指定路径；显式参数优先于 `FUNMOVIE_DB_PATH` 环境变量，后者优先于默认位置。`funmovie/database/core_redis.py` 里还提供了一个 `RedisClient`，可以选择把磁力链接存到 Redis 而不是 SQLite。

### 4. 磁力链接转种子下载（依赖本地 aria2c）

```bash
python -m funmovie.magnet.magnet_to_torrent_aria2c --save-path ./torrents
```

需要本地跑一个开启了 RPC 的 aria2c（默认连接 `127.0.0.1:6800`），会从数据库里取出待下载的磁力链接，通过 `aria2.addUri` 提交下载任务。保存目录的优先级为命令行参数 `--save-path`、环境变量 `FUNMOVIE_SAVE_PATH`、安全默认值 `~/.cache/funmovie/torrents`。

### 5. 解析 .torrent 文件

```python
from funmovie.magnet.parse_torrent import ParserTorrent

info = ParserTorrent("/path/to/xxx.torrent")
print(info.get_filename())
```

### 6. DHT 采集服务的统一启停

`funmovie.magnet.core`（内部调用 `crawler.start_server()`）是仓库里唯一的长期运行服务，
统一通过 `scripts/setup.sh` 管理：

```bash
scripts/setup.sh start dev     # 后台启动（源码树，dev 环境）
scripts/setup.sh run dev       # 前台运行，便于调试
scripts/setup.sh status        # 查看 dev/prod 两个环境的运行状态
scripts/setup.sh stop dev      # 停止（连同 start_server() 派生的子进程一并终止）
scripts/setup.sh start prod    # 生产启动，要求先安装上面构建的 wheel（非 editable）
```

PID、日志统一放在 `.run/` 下。aria2 下载提交（`magnet_to_torrent_aria2c`）和种子解析
（`parse_torrent`）是独立的一次性批处理任务，不受本脚本管理，按上面第 4、5 节单独运行。

## 已知局限（如实说明）

- `funmovie/magnet/crawler.py` 实现了一个简化版 DHT 爬虫（`DHTServer`），会直接从 BT 网络里嗅探 info_hash；`funmovie/magnet/magnet_to_torrent_aria2c.py` 会通过 aria2c 提交下载任务 —— 这两个文件的网络/RPC 调用都已收进 `if __name__ == "__main__":`，作为脚本运行（`python -m ...`）才会触发，单纯 `import` 不会有副作用。
- `add_magnet` 使用 SQLite 的 `insert or ignore`：新链接会插入，主键重复的链接保持原记录不变。
- 爬取的目标站点、tracker 列表等均为历史遗留配置，可能已失效，需要自行更新维护。

## 关于 farfarfun

[farfarfun](https://github.com/farfarfun) 是一个专注于实用工具库的开源组织，
涵盖云存储、数据处理、AI、多媒体与开发工具链等方向。

- 🏠 组织主页：<https://github.com/farfarfun>
- 📦 PyPI：<https://pypi.org/user/niuliangtao/>
- 📧 联系：farfarfun@qq.com

本项目基于 [MIT](LICENSE) 协议开源。
