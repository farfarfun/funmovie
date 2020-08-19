from notedrive.magnet.core import Magnet2Torrent
from notemovie.database.job import get_magnets, update_status

mt = Magnet2Torrent(use_additional_trackers=True)

for magnet in get_magnets(1000):
    print(magnet)
    torrent = mt.get_magnet_info(magnet_link=magnet)
    print(torrent)
    if torrent is None:
        update_status(magnet, -1)
    else:
        update_status(magnet, 1)
