# Changelog

## Unreleased

### 变更

- 包名从 `notemovie` 改为 `funmovie`，与仓库名保持一致（`note*` → `fun*` 清理，farfarfun/todo-list#298）。导入名与 `pyproject.toml` 里声明的 PyPI 包名同步修改：
  - `import notemovie...` → `import funmovie...`
  - PyPI 包名 `notemovie` → `funmovie`
  - 已核实 `pip index versions notemovie`：旧名下从未发布过任何版本，无需发转发版。如果之后有变化，给 `notemovie` 发一个指向 `funmovie` 的转发版本需要仓库所有者手动跟进，本次不做自动化处理。
- 目录结构调整为 `src/funmovie/` 布局，`pyproject.toml` 改用 `hatchling` 构建后端，依赖管理迁移到 `uv`（声明版本下限 + `uv.lock`）。
- 依赖声明修正：移除尚无可安装版本的 `farfuntool`，改用标准库 `sqlite3` 完成本项目所需的数据库操作；`bencoder`（0.2.0，只有 `encode`/`decode`）改为 `bencoder.pyx`（提供代码实际使用的 `bencode`/`bdecode` API）。
- 日志统一改用 `farlog`，替换原来自建的 `logging`/`print`。
- `script/build.sh` 改为统一调用 `uvx funbuild`，不再手写 `setup.py`/`twine` 发布流程。

### 修复

- `database/core.py` 的 `get_magnets()` 拼 SQL 时误用了字面量字符串 `"table_name"`，而不是插入 `self.table_name`，导致查询恒失败（`no such table: table_name`）。
- `database/job.py` 的 `update_status()` 把整型变量 `status` 当成 dict 的 key 用（`{"magnet": ..., status: status}`），而不是字符串 `"status"`，导致状态更新实际不生效。
- `magnet/crawler.py` 顶层无条件调用 `open("./tracks/all.txt", ...)`，在缺少该相对路径文件时会导致模块 `import` 即崩溃，并悄悄覆盖了上面已经写好的硬编码 tracker 列表；已删除该行。
- `magnet/crawler.py`、`magnet/magnet_to_torrent_aria2c.py` 顶层分别无条件调用 `start_server()` / `magnet2torrent()`，导致单纯 `import` 这两个模块就会触发真实的网络/RPC 调用；已收进 `if __name__ == "__main__":`。
- 修正多处裸 `except:`/宽泛 `except Exception` 吞异常的写法，改为按实际可能抛出的异常类型捕获并记录日志。
- `library/get_magnet.py`、`utils/core.py`、`magnet/magnet_to_torrent_aria2c.py`、
  `magnet/crawler.py`（3 处）、`magnet/tracker_list.py` 共 7 处日志误用 stdlib logging
  的 `%s` 占位符，farlog（loguru）不支持该语法，参数被静默丢弃；统一改为 `{}` 占位符。

### 新增

- 补充 `tests/`：覆盖迅雷链接解码、磁力链接的增删改查、`.torrent` 元信息解析等真实用例（此前测试仅做 import 冒烟测试）。
- README 补充 `farfarfun` 组织信息与 MIT 协议声明。
- 新增 `scripts/setup.sh`：统一管理 `funmovie.magnet.core`（DHT 采集服务）的
  `start`/`run`/`stop`/`status`，dev 直接跑源码树、prod 强制校验已安装的正式包，
  PID/日志落在 `.run/`，`stop` 会连同 `start_server()` 派生的多进程子进程一并终止。
  README 补充对应用法说明。

### 修复（第二轮，farfarfun/todo-list#735）

- **严重**：`magnet/crawler.py` 的 `BOOTSTRAP_NODES` 混入了一批 `udp://`/`http://`
  形式的 BT tracker announce URL（而非 DHT 节点地址）。`socket.sendto()` 只接受
  `(host, port)` 元组，传入字符串会抛出 `TypeError`，且该异常不是 `OSError`，
  不会被 `send_krpc()` 的 `except OSError` 捕获——服务一启动、第一次
  `bootstrap()` 就会让线程崩溃，`start_server()` 实际从未真正跑起来过。
  现在只保留真正的 DHT 引导节点（`router.bittorrent.com` 等 3 个）。
- `magnet/crawler.py` 的 `on_message()` 用 `except KeyError: pass` 静默吞掉异常，
  改为记录地址和缺失字段后丢弃。
- `magnet/crawler.py` 的 KRPC 调试日志会把完整报文（可能包含 `token` 等协议凭据）
  写入日志，改为只记录地址与消息类型（`y`/`q`）。
- `magnet/magnet_to_torrent_aria2c.py` 的 `exec_rpc()` 在 aria2 返回 `error` 时
  只记日志就返回，`main()` 仍以 0 退出；改为抛出 `Aria2RpcError`，
  `magnet2torrent()` 捕获后继续处理其余磁力链接并统计失败数，
  `main()` 只要有失败就以非 0 退出。
- `magnet/parse_torrent.py` 的 `get_createby()` 标注为 `str | None`，但直接返回
  `bdecode()` 产出的 `bytes`；改为按 utf-8 解码，解码失败时退化为十六进制字符串。
- `magnet/core.py` 的 `command_line_runner()` 依次调用 `start_server()`、
  `magnet2torrent()`、`parse_torrent()`，但 `start_server()` 内部线程永久阻塞，
  后两个调用永远不可达；改为只保留 `start_server()`，aria2 下载与种子解析作为
  独立的一次性任务按 README 用法单独运行。
- `library/get_magnet.py` 的 `get_magnet()` docstring 称会 "upsert"，实际是
  `insert or ignore`（重复主键保持原记录不变）；改为准确描述。
- `script/clear_history.sh` 没有 `set -euo pipefail`，任一步失败仍可能继续执行
  后续的 `git branch -D`/`git push -f` 等破坏性操作；补上失败即退出，并要求
  显式传入 `--yes` 才会真正执行，同时校验当前目录是 git 仓库且存在 `origin` 远端。
