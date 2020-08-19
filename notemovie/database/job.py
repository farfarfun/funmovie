from notemovie.database.core import MovieManage, MagnetManage

manage = MovieManage()
manage.create()
magnet = MagnetManage()
magnet.create()


def add_magnet(magnet_str: str):
    if magnet_str.startswith('magnet'):
        magnet.insert({"magnet": magnet_str})


def get_magnet():
    return magnet.get_magnets(1)[0]


def get_magnets(size=10, status=0):
    return magnet.get_magnets(size)


def update_status(magnet_link, status=1):
    magnet.update({"magnet": magnet_link, status: status})
