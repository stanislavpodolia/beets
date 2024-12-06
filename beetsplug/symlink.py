import os
import errno
from beets import config
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand, _open_library
from beets.util import syspath
from beets.library import Item, Album
import re
import threading

rootDir = 'D:/Music/Record Labels/'

def sanitize(name):
    return re.sub(r'[\\/*?:"<>|]', "_", name)

class symlink_item_thread(threading.Thread):
    def __init__(self, dst_dir, item):
        threading.Thread.__init__(self)
        self.dst_dir = dst_dir
        self.item = item
    def run(self):
        dst_file = os.path.join(self.dst_dir, os.path.basename(self.item.path.decode('utf8')))
        try:
            if os.path.islink(dst_file):
                os.remove(dst_file)
            os.symlink(self.item.path.decode('utf8'), dst_file)
        except:
            print('Cant symlink', self.item.path.decode('utf8'))
            return
            # except OSError as exc:
                # if exc.errno != errno.EEXIST:
                #     raise
class remove_symlink_item_thread(threading.Thread):
    def __init__(self, dst_dir, item):
        threading.Thread.__init__(self)
        self.dst_dir = dst_dir
        self.item = item
    def run(self):
        dst_file = os.path.join(self.dst_dir, os.path.basename(self.item.path.decode('utf8')))
        if os.path.islink(dst_file):
            try:
                os.remove(dst_file)
                if len(os.listdir(self.dst_dir)) == 0:
                    os.rmdir(self.dst_dir)
            except:
                print('Cant remove symlink', dst_file)
                return

def album_imported(album):
    if album.catalognum and album.label:
        dst_dir = os.path.join(
            'D:/Music/Record Labels/',
            sanitize(album.label),
            sanitize('[{0}] {1} - {2}'.format(album.catalognum, album.albumartist, album.album))
        )

        if not os.path.exists(dst_dir):
            try:
                os.makedirs(dst_dir)
            except:
                print('Cant makedirs', dst_dir)
                return
            # except OSError as exc:
            #     if exc.errno != errno.EEXIST:
            #         raise

        threads = []

        for item in album.items(None, None, 'id, path'):
            t = symlink_item_thread(dst_dir, item)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

def item_removed(item):
    try:
        lib = _open_library(config)
        if isinstance(item, Item):
            album_id = item.album_id
            album = lib.get_album(album_id)
            dst_dir = os.path.join(
                rootDir,
                sanitize(album.label),
                sanitize('[{0}] {1} - {2}'.format(album.catalognum, album.albumartist, album.album))
            )

            t = remove_symlink_item_thread(dst_dir, item)
            t.start()
            t.join()
        elif isinstance(item, Album):
            album_id = item.id
            album = lib.get_album(album_id)
            dst_dir = os.path.join(
                rootDir,
                sanitize(album.label),
                sanitize('[{0}] {1} - {2}'.format(album.catalognum, album.albumartist, album.album))
            )

            threads = []

            for item in album.items():
                t = remove_symlink_item_thread(dst_dir, item)
                t.start()
                threads.append(t)

            for t in threads:
                t.join()
    except:
        return

class album_imported_thread(threading.Thread):
    def __init__(self, album):
        threading.Thread.__init__(self)
        self.album = album
    def run(self):
        return album_imported(self.album)

class check_path(threading.Thread):
    def __init__(self, file):
        threading.Thread.__init__(self)
        self.file = file
    def run(self):
        if not os.path.exists(os.readlink(self.file)):
            print(self.file, 'broken')

class SymlinkLibraryCommand(Subcommand):
    def __init__(self):
        super(SymlinkLibraryCommand, self).__init__(
            name='symlink_library',
            help='Create symlinks for the entire library.'
        )
        self.func = self.run

    def run(self, lib, opts, args):
        # threads = []

        # for root, dirs, files in os.walk('D:/Music/Record Labels/'):
        #     for file in files:
        #         t = check_path(os.path.join(root, file))
        #         t.start()
        #         threads.append(t)

        # for t in threads:
        #     t.join()

        threads = []

        for album in lib.albums(None, None, None, 'id, catalognum, albumartist, album, label'):
            t = album_imported_thread(album)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        folders = list(os.walk(rootDir))[1:]

        for folder in folders:
            if not folder[2]:
                os.rmdir(folder[0])

class MySymlinkPlugin(BeetsPlugin):
    def __init__(self):
        super(MySymlinkPlugin, self).__init__()
        self.register_listener('album_imported', self.album_imported)
        # self.register_listener('item_removed', self.item_removed)

    def commands(self):
        return [SymlinkLibraryCommand()]

    def album_imported(self, lib, album):
        album_imported(album)

    def item_removed(self, item):
        item_removed(item)