#!/usr/bin/env python

"""
Download orphaned photos from Flickr.
"""

import argparse
import datetime
from pathlib import Path
import random
import sqlite3
import sys
import time
import tomllib

import dateutil.parser
import flickr_api as flickr
import regex as re
import requests

# pylint: disable=global-statement
VERBOSE = False

sqlite3.register_adapter(bool, int)
sqlite3.register_converter("BOOLEAN", lambda v: bool(int(v)))

class FlickrCallFailed (flickr.FlickrError):
    "whenever we catch some kind of error calling Flickr API..."


def eprint(*args, file=sys.stderr, **kwds):
    "error print"
    now = datetime.datetime.now().strftime("%T")
    return print(now, *args, file=file, **kwds) if VERBOSE else None


def func_name(func):
    "I would have thought inspect could do this"
    if hasattr(func, "__qualname__"):
        return func.__qualname__
    if hasattr(func, "__name__"):
        return func.__name__
    if hasattr(func, "__func__"):
        return func_name(func.__func__)
    return "<unknown>"

class FlickrAPI:
    "Call flickr method, doing a bit of housekeeping along the way"
    def __init__(self):
        self.n_calls = 0
        self.n_timeouts = 0
        self.n_errors = 0

    @property
    def total_errors(self):
        "return current total error and timeout values"
        return self.n_timeouts + self.n_errors

    def call_flickr(self, method, *args, **kwds):
        "Make a call via the Flickr API."

        self.n_calls += 1
        if self.n_calls % 50 == 0:
            # pause to avoid clampdown by Flickr? ¯\_(ツ)_/¯
            pause = random.random() * 7           # nosec
            eprint(f"pause {pause:.2f}s (calls: {self.n_calls})")
            time.sleep(pause)

        name = func_name(method)
        eprint(f"calling: {name}(*{args}, **{kwds})")
        while True:
            try:
                result = method(*args, **kwds)
                self.n_timeouts = self.n_errors = 0
                return result
            except flickr.FlickrError as exc:
                errmsg = re.sub("<html[^>]*>.*</html>",
                    "<html> ... (elided) ...</html>",
                    str(exc), flags=re.DOTALL)
                self.n_errors += 1
                eprint(f"{name} error, pause 15s")
                if self.total_errors >= 10:
                    raise FlickrCallFailed(errmsg) from exc
                time.sleep(15)
            except requests.Timeout as exc:
                self.n_timeouts += 1
                if self.total_errors >= 10:
                    raise FlickrCallFailed("timeout") from exc
            except OSError as exc:
                self.n_errors += 1
                eprint(f"{name} error, pause 15s")
                if self.total_errors >= 10:
                    raise FlickrCallFailed(str(exc)) from exc
                time.sleep(15)

FLICKR_API = FlickrAPI()

def populate_photos_db(photos, album, db):
    cur = db.cursor()
    cur.execute("begin")

    for photo in photos:
        try:
            url = FLICKR_API.call_flickr(photo.getPageUrl)
            url = url.replace("http://", "https://")
            info = FLICKR_API.call_flickr(photo.getInfo)
        except FlickrCallFailed:
            eprint("error retrieving info for", photo)
            continue
        n = cur.execute(
            "select count(*) from photos"
            "  where id = ?", (photo.id,)).fetchone()[0]
        if n == 0:
            created = int(dateutil.parser.parse(info["taken"]).strftime("%s"))
            cur.execute(
                "insert into photos"
                "  (id, title, description, created, url)"
                "    VALUES"
                "  (?, ?, ?, ?, ?)",
                (photo.id, photo.title, photo.description, created, url))
            cur.execute(
                "insert into album2photos"
                "  (album, photo)"
                "    VALUES"
                "  (?, ?)",
                (album.id, photo.id))
        else:
            # make sure title, description and url are up-to-date (description
            # field wasn't in the original schema).
            cur.execute(
                "update photos"
                "  set title = ?,"
                "    description = ?,"
                "    url = ?"
                "  where id = ?",
                (photo.title, photo.description, url, photo.id))
    db.commit()

def best_size(photo):
    """As a free user I can no longer download "Original" all the time."""
    best = 0
    label = ""
    sizes = photo.getSizes()
    for key in sizes:
        size = sizes[key]
        try:
            pixels = int(size["height"]) * int(size["width"])
        except TypeError:
            eprint(f"error processing {size}")
            continue
        if pixels > best:
            best = pixels
            label = key
            eprint(best, label)
    return label

def load_photos(container, db, maxphotos=0):
    if not hasattr(container, "getPhotos"):
        raise AttributeError(f"{container} has no getPhotos attribute.")

    photos = set()
    page = 1
    page_size = 250 if maxphotos == 0 else min(250, maxphotos)
    eprint(f"Download up to {page_size} photos from {container}")
    while True:
        try:
            new_photos = FLICKR_API.call_flickr(container.getPhotos,
                per_page=page_size, page=page)
        except FlickrCallFailed:
            break

        eprint(f"found {len(new_photos)} images, page size {page_size}")
        populate_photos_db(new_photos, container, db)

        photos |= set(new_photos)

        if len(new_photos) < page_size:
            break
        page += 1

    eprint(len(photos), "photos")
    return photos

def classify_photos(photos):
    orphans = set()
    rest = set()
    errors = set()
    n = 0
    for photo in photos:
        try:
            album_context = FLICKR_API.call_flickr(photo.getAllContexts)
            album_context = album_context[0]
        except FlickrCallFailed as exc:
            errors.add(photo)
            eprint("error getting contexts for", photo, exc)
            continue

        if not album_context:
            orphans.add(photo)
            continue

        if len(album_context) == 1:
            photoset = album_context[0]
            if photoset.title == "Auto Upload":
                orphans.add(photo)
                continue

        rest.add(photo)
        n += 1
        if n % 25 == 0:
            eprint("... photos:", len(rest),
                   "orphans:", len(orphans),
                   "errors:", len(errors))

    eprint("photos:", len(rest),
           "orphans:", len(orphans),
           "errors:", len(errors))

    return orphans, errors, rest


def save_photos(photos, user, db, outputdir="."):
    if not photos:
        return
    eprint(f"saving {len(photos)} photos to {outputdir}")
    outputdir = Path(outputdir)
    outputdir.mkdir(parents=True, exist_ok=True)

    cur = db.cursor()
    cur.execute("BEGIN")
    for (n, photo) in enumerate(photos):
        if (n+1) % 100 == 0:
            eprint("... photos:", n+1)
        filename = outputdir.joinpath(f"{user.id}.{photo.id}.jpg")
        if filename.exists():
            continue
        try:
            FLICKR_API.call_flickr(photo.save, filename,
                                   size_label=best_size(photo))
        except FlickrCallFailed as exc:
            eprint(f"error saving {filename} ({exc})")
        else:
            cur.execute("update photos set deleted = 0"
                        "  where id = ?", (photo.id,))
    db.commit()


def delete_photos(photos, db):
    if not photos:
        return

    yn = input(f"Delete {len(photos)} photos (y/n)? ")   # nosec
    if not yn or yn.lower()[0] != "y":
        eprint("Delete not confirmed.")
        return

    cur = db.cursor()
    cur.execute("begin")
    for (n, photo) in enumerate(photos):
        if (n+1) % 100 == 0:
            eprint("... photos:", n+1)
        try:
            FLICKR_API.call_flickr(photo.delete)
        except FlickrCallFailed as exc:
            eprint(f"error deleting photo {photo.id} ({exc})")
        else:
            cur.execute("update photos set deleted = 1"
                        "  where id = ?", (photo.id,))
    db.commit()


def flickr_login(username):
    with open("flickr_keys.toml", "rb") as keyfile:
        keys = tomllib.load(keyfile)
    flickr.set_keys(api_key=keys["API_KEY"], api_secret=keys["API_SECRET"])
    flickr.set_auth_handler("./flickr_auth")
    flickr.enable_cache()
    return FLICKR_API.call_flickr(flickr.Person.findByUserName, username)


def get_album(album_name, user, db):
    albums = FLICKR_API.call_flickr(user.getPhotosets)

    # Take the opportunity to populate albums table
    cur = db.cursor()
    cur.execute("begin")
    for album in albums:
        url = f"https://www.flickr.com/photos/{album.owner}/albums/{album.id}"
        n = cur.execute(
            "select count(*) from albums"
            "  where id = ?", (album.id,)).fetchone()[0]
        if n == 0:
            cur.execute(
                "insert into albums"
                "  (id, title, description, created, url)"
                "    VALUES"
                "  (?, ?, ?, ?, ?)",
                (album.id, album.title, album.description, album.date_create, url))
            eprint(f"Inserted {album} in db")
        else:
            # make sure title, description and url are up-to-date (description
            # field wasn't in the original schema).
            cur.execute(
                "update albums"
                "  set title = ?,"
                "    description = ?,"
                "    url = ?"
                "  where id = ?",
                (album.title, album.description, url, album.id))
    db.commit()

    try:
        return [album for album in albums if album.title == album_name][0]
    except IndexError:
        eprint(f"Can't find an album named {album_name}")
        raise


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", dest="verbose", action="store_true")
    parser.add_argument("-s", "--save", dest="save",
                        help="save orphaned photos to this dir")
    parser.add_argument("--delete-all", dest="delete_all", default=False,
                        action="store_true",
                        help="if given, delete all photos, not just orphans")
    parser.add_argument("--delete-orphans", dest="delete_orphans", action="store_true",
                        help="delete orphaned photos", default=False)
    parser.add_argument("-m", "--maxphotos", dest="maxphotos", type=int,
                        help="max # of photos to download", default=0)
    parser.add_argument("-u", "--user", dest="user", required=True, help="Flickr username")
    parser.add_argument("-d", "--database", help="SQLite3 database filename",
                        default=":memory:")
    parser.add_argument("-a", "--album", dest="album_name", help="Album to download",
                        default=None)
    return parser.parse_args()

def get_db_connection(sqldb):
    conn = sqlite3.Connection(sqldb)
    try:
        conn.execute("select count(*) from photos")
    except sqlite3.OperationalError:
        conn.execute("""
        create table photos (
          id TEXT PRIMARY KEY,
          title TEXT,
          description TEXT DEFAULT "",
          url TEXT,
          created INTEGER,
          taken INTEGER,
          deleted INTEGER DEFAULT 0
        )""")

        conn.execute("""
        create table albums (
          id TEXT PRIMARY_KEY,
          title TEXT,
          description TEXT DEFAULT "",
          created INTEGER,
          url TEXT
        )""")

        conn.execute("""
        create table album2photos (
          album TEXT,
          photo TEXT,
          FOREIGN KEY(album) REFERENCES albums(id),
          FOREIGN KEY(photo) REFERENCES photos(id)
        )""")

    return conn


def main():
    global VERBOSE

    args = parse_args()

    VERBOSE = args.verbose

    user = flickr_login(args.user)

    db = get_db_connection(args.database)

    if args.album_name is not None:
        container = get_album(args.album_name, user, db)
    else:
        # Operate on the photostream (I think)
        container = user
    photos = load_photos(container, maxphotos=args.maxphotos, db=db)

    orphans, errors, rest = classify_photos(photos)
    eprint(f"{len(orphans)} orphans")
    eprint(f"{len(errors)} uncategorized due to errors")
    eprint(f"{len(rest)} everything else")

    if args.save is not None:
        eprint("saving photos to", args.save)
        save_photos(orphans, user, db, args.save)
        save_photos(errors, user, db, args.save)
        save_photos(rest, user, db, args.save)

    if args.delete_orphans:
        delete_photos(orphans, db)
        if args.delete_all:
            delete_photos(errors, db)
            delete_photos(rest, db)

    return 0


if __name__ == "__main__":
    sys.exit(main())
