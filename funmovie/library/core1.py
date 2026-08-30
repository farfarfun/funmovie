# NOTE: notedrive.magnet.core.Magnet2Torrent is not exported by any published notedrive/fundrive
# release (source moved to notedrive/others/magnet/core.py, never re-exported) — this script is
# already broken pre-migration and has no callers elsewhere in the repo. Left as-is rather than
# forcing a fake fundrive substitution; see farfarfun/todo-list#300.
from notedrive.magnet.core import Magnet2Torrent
from funmovie.database.job import get_magnets, update_status

mt = Magnet2Torrent(use_additional_trackers=True)

for magnet in get_magnets(1000):
    print(magnet)
    torrent = mt.get_magnet_info(magnet_link=magnet)
    print(torrent)
    if torrent is None:
        update_status(magnet, -1)
    else:
        update_status(magnet, 1)
