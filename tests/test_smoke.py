import base64
import os
import tempfile

import pytest
from bencoder import bencode

import funmovie
import funmovie.utils
from funmovie.database.core import MagnetManage, MovieManage
from funmovie.magnet.parse_torrent import ParserTorrent
from funmovie.utils import thunder2magnet, thunder2url


def test_import_funmovie():
    assert funmovie is not None


def test_import_funmovie_utils():
    assert funmovie.utils is not None


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
