import base64
import json
import os
import sys
import tempfile

import pytest
from bencoder import bencode

import funmovie
import funmovie.utils
from funmovie.database import job
from funmovie.database import core_redis
from funmovie.database.core import MagnetManage, MovieManage
from funmovie.magnet import crawler, magnet_to_torrent_aria2c, tracker_list
from funmovie.magnet.crawler import DHTServer
from funmovie.library import get_magnet as get_magnet_module
from funmovie.magnet.parse_torrent import ParserTorrent
from funmovie.utils import thunder2magnet, thunder2url


def test_import_funmovie():
    assert funmovie is not None


def test_import_funmovie_utils():
    assert funmovie.utils is not None


def test_import_database_job_does_not_create_database(tmp_path, monkeypatch):
    database_path = tmp_path / "movieset.db"
    monkeypatch.setattr(job, "manage", None)
    monkeypatch.setattr(job, "magnet", None)
    assert not database_path.exists()


THUNDER_URL = (
    "thunder://"
    + base64.b64encode(
        ("AA" + "magnet:?xt=urn:btih:aaaa" + "ZZ").encode("gbk")
    ).decode()
)


def test_thunder2url_decodes_thunder_link():
    assert thunder2url(THUNDER_URL) == "magnet:?xt=urn:btih:aaaa"


def test_thunder2url_passthrough_for_non_thunder_link():
    assert thunder2url("magnet:?xt=urn:btih:bbbb") == "magnet:?xt=urn:btih:bbbb"


def test_thunder2url_returns_original_on_decode_error():
    bad_url = "thunder://not-base64-!!!"
    assert thunder2url(bad_url) == bad_url


def test_thunder2magnet_extracts_magnet_link():
    assert thunder2magnet(THUNDER_URL) == "magnet:?xt=urn:btih:aaaa"


def test_thunder2magnet_returns_empty_for_non_magnet_result():
    non_magnet = "thunder://" + base64.b64encode("AAhelloZZ".encode("gbk")).decode()
    assert thunder2magnet(non_magnet) == ""


@pytest.fixture
def magnet_manage():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        manage = MagnetManage(db_path=db_path)
        manage.create()
        yield manage


def test_magnet_manage_insert_and_get(magnet_manage):
    magnet_manage.insert({"magnet": "magnet:?xt=urn:btih:cccc"})
    magnets = magnet_manage.get_magnets(size=10)
    assert magnets == ["magnet:?xt=urn:btih:cccc"]


def test_magnet_manage_update_status_excludes_from_pending(magnet_manage):
    magnet_manage.insert({"magnet": "magnet:?xt=urn:btih:dddd"})
    magnet_manage.update({"magnet": "magnet:?xt=urn:btih:dddd", "status": 1})
    assert magnet_manage.get_magnets(size=10) == []


def test_magnet_manage_empty_result(magnet_manage):
    assert magnet_manage.get_magnets(size=10) == []


def test_job_functions_use_explicit_database(tmp_path, monkeypatch):
    monkeypatch.setattr(job, "manage", None)
    monkeypatch.setattr(job, "magnet", None)
    job.initialize(str(tmp_path / "job.db"))
    job.add_magnet("magnet:?xt=urn:btih:eeee")
    assert job.get_magnets() == ["magnet:?xt=urn:btih:eeee"]
    job.update_status("magnet:?xt=urn:btih:eeee")
    assert job.get_magnets() == []


@pytest.fixture
def movie_manage():
    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = os.path.join(tmp_dir, "test.db")
        manage = MovieManage(db_path=db_path)
        manage.create()
        yield manage


def test_movie_manage_create_and_insert(movie_manage):
    movie_manage.insert({"url": "http://example.com/a.torrent", "name": "示例"})
    rows = list(movie_manage.select("select url, name from movies"))
    assert rows == [("http://example.com/a.torrent", "示例")]


def _build_single_file_torrent(tmp_path):
    torrent_path = os.path.join(tmp_path, "single.torrent")
    meta = {
        b"announce": b"test",
        b"info": {b"name": b"a.mp4", b"length": 100},
    }
    with open(torrent_path, "wb") as f:
        f.write(bencode(meta))
    return torrent_path


def test_parser_torrent_single_file(tmp_path):
    torrent_path = _build_single_file_torrent(str(tmp_path))
    parser = ParserTorrent(torrent_path)
    assert parser.is_files() is False
    assert parser.get_filename() == "a.mp4"


def _build_multi_file_torrent(tmp_path):
    torrent_path = os.path.join(tmp_path, "multi.torrent")
    meta = {
        b"announce": b"test",
        b"info": {
            b"name": b"dir",
            b"files": [{b"length": 10, b"path": [b"a.txt"]}],
        },
    }
    with open(torrent_path, "wb") as f:
        f.write(bencode(meta))
    return torrent_path


def test_parser_torrent_multi_file(tmp_path):
    torrent_path = _build_multi_file_torrent(str(tmp_path))
    parser = ParserTorrent(torrent_path)
    assert parser.is_files() is True
    filenames = dict(parser.get_filename())
    assert filenames["path"] == ["a.txt"]


def test_get_track_writes_response_to_requested_directory(tmp_path, monkeypatch):
    class Response:
        text = "udp://one\n\nudp://two\n"

        def raise_for_status(self):
            return None

    monkeypatch.setattr(tracker_list.requests, "get", lambda url, timeout: Response())
    assert tracker_list.get_track("https://example.com/all.txt", tmp_path) == [
        "udp://one",
        "udp://two",
    ]
    assert (tmp_path / "all.txt").read_text() == "udp://one\nudp://two"


def test_exec_rpc_uses_configured_save_path(tmp_path, monkeypatch):
    requests = []

    class Response:
        def read(self):
            return b"{}"

    class Connection:
        def __init__(self, host, port):
            assert (host, port) == ("127.0.0.1", 6800)

        def request(self, method, path, body, headers):
            requests.append(json.loads(body))

        def getresponse(self):
            return Response()

    monkeypatch.setattr(magnet_to_torrent_aria2c, "HTTPConnection", Connection)
    magnet_to_torrent_aria2c.exec_rpc("magnet:test", tmp_path)
    assert requests[0]["params"][1]["dir"] == str(tmp_path)


def test_exec_rpc_raises_on_aria2_error(tmp_path, monkeypatch):
    class Response:
        def read(self):
            return b'{"error": {"message": "failed"}}'

    class Connection:
        def __init__(self, host, port):
            pass

        def request(self, method, path, body, headers):
            pass

        def getresponse(self):
            return Response()

    monkeypatch.setattr(magnet_to_torrent_aria2c, "HTTPConnection", Connection)
    with pytest.raises(magnet_to_torrent_aria2c.Aria2RpcError):
        magnet_to_torrent_aria2c.exec_rpc("magnet:test", tmp_path)


def test_magnet2torrent_counts_failures_without_stopping(tmp_path, monkeypatch):
    monkeypatch.setattr(
        magnet_to_torrent_aria2c,
        "get_magnets",
        lambda: iter(["magnet:a", "magnet:b", "magnet:c"]),
    )

    calls = []

    def fake_exec_rpc(magnet, save_path):
        calls.append(magnet)
        if magnet == "magnet:b":
            raise magnet_to_torrent_aria2c.Aria2RpcError("boom")

    monkeypatch.setattr(magnet_to_torrent_aria2c, "exec_rpc", fake_exec_rpc)
    failures = magnet_to_torrent_aria2c.magnet2torrent(tmp_path)
    assert calls == ["magnet:a", "magnet:b", "magnet:c"]
    assert failures == 1


def test_main_exits_non_zero_when_any_submission_fails(monkeypatch):
    monkeypatch.setattr(magnet_to_torrent_aria2c, "magnet2torrent", lambda save_path: 2)
    monkeypatch.setattr(sys, "argv", ["magnet_to_torrent_aria2c"])
    with pytest.raises(SystemExit) as exc_info:
        magnet_to_torrent_aria2c.main()
    assert exc_info.value.code == 1


def test_redis_client_delegates_to_set_operations(monkeypatch):
    class Redis:
        def __init__(self, connection_pool):
            self.values = set()

        def sadd(self, key, value):
            self.values.add(value.encode())

        def srandmember(self, key, count):
            return list(self.values)[:count]

    monkeypatch.setattr(core_redis.redis, "ConnectionPool", lambda **kwargs: object())
    monkeypatch.setattr(core_redis.redis, "Redis", Redis)
    client = core_redis.RedisClient()
    client.add_magnet("magnet:test")
    assert client.get_magnets() == [b"magnet:test"]


def test_web_crawler_handles_request_failure(monkeypatch):
    def fail(url, timeout):
        raise get_magnet_module.requests.RequestException("offline")

    monkeypatch.setattr(get_magnet_module.requests, "get", fail)
    get_magnet_module.web1(1, 2)


def test_dht_server_ignores_malformed_message():
    server = object.__new__(DHTServer)
    logged = []
    server.logger = type(
        "_StubLogger",
        (),
        {"debug": staticmethod(lambda *a, **kw: logged.append((a, kw)))},
    )()
    server.on_message({}, ("127.0.0.1", 6881))
    assert len(logged) == 1


def test_bootstrap_nodes_are_valid_socket_addresses():
    # BOOTSTRAP_NODES 必须是 (host, port) 元组，不能混入 URL 字符串：
    # 混入字符串会让 udp.sendto() 抛出 TypeError（不是 OSError），不会被
    # send_krpc() 的 except OSError 捕获，导致 bootstrap() 整线程崩溃。
    for node in crawler.BOOTSTRAP_NODES:
        assert isinstance(node, tuple)
        host, port = node
        assert isinstance(host, str)
        assert isinstance(port, int)


def test_bootstrap_sends_without_crashing_on_unreachable_node(monkeypatch):
    server = object.__new__(DHTServer)
    server.nid = b"0" * 20

    class FakeSocket:
        def sendto(self, data, address):
            raise OSError("network unreachable")

    server.udp = FakeSocket()
    logged = []
    server.logger = type(
        "_StubLogger",
        (),
        {"warning": staticmethod(lambda *a, **kw: logged.append((a, kw)))},
    )()
    server.bootstrap()
    assert len(logged) == len(crawler.BOOTSTRAP_NODES)
