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

class FlickrCallFailed (flickr.FlickrError):
    "whenever we catch some kind of error calling Flickr API..."


def eprint(*args, file=sys.stderr, **kwds):
    "error print"
    now = datetime.datetime.now().strftime("%T")
    return print(now, *args, file=file, **kwds) if VERBOSE else None


def call_flickr(method, *args, **kwds):
    name = method.__qualname__ if hasattr(method, "__qualname__") else method.__name__
    eprint(f"calling: {name}(*{args}, **{kwds})")
    try:
        return method(*args, **kwds)
    except flickr.FlickrError as exc:
        errmsg = re.sub("<html[^>]*>.*</html>",
            "<html> ... (elided) ...</html>",
            str(exc), flags=re.DOTALL)
        eprint("Pause 15s")
        time.sleep(15)
        raise FlickrCallFailed(errmsg) from exc
    except requests.Timeout:
        raise FlickrCallFailed("timeout") from exc
    except OSError as exc:
        eprint("Pause 15s")
        time.sleep(15)
        raise FlickrCallFailed(str(exc)) from exc

def populate_photos_db(photos, album, db):
    cur = db.cursor()
    cur.execute("begin")

    for photo in photos:
        n = cur.execute(
            "select count(*) from photos"
            "  where id = ?", (photo.id,)).fetchone()[0]
        if n == 0:
            url = photo.getPageUrl().replace("http://", "https://")
            info = photo.getInfo()
            created = int(dateutil.parser.parse(info["taken"]).strftime("%s"))
            cur.execute(
                "insert into photos"
                "  (id, title, created, url)"
                "    VALUES"
                "  (?, ?, ?, ?)",
                (photo.id, photo.title, created, url))
            cur.execute(
                "insert into album2photos"
                "  (album, photo)"
                "    VALUES"
                "  (?, ?)",
                (album.id, photo.id))
    db.commit()

def load_photos(container, db, maxphotos=0):
    if not hasattr(container, "getPhotos"):
        raise AttributeError(f"{container} has no getPhotos attribute.")

    photos = set()
    ids = set()
    page = 1
    nerrs = timeouts = 0
    while True:
        page_size = 500 if maxphotos == 0 else min(500, maxphotos)

        eprint(f"Download up to {page_size} photos from {container}")
        try:
            new_photos = call_flickr(container.getPhotos,
                per_page=page_size, page=page)
        except FlickrCallFailed as exc:
            if str(exc) == "timeout":
                timeouts += 1
                if timeouts >= 10:
                    eprint("Too many timeouts")
                    break
                continue
            nerrs += 1
            eprint(f"Error {container}: {exc}")
            if nerrs >= 10:
                eprint("Too many errors, giving up")
                break
            continue

        eprint(f"found {len(new_photos)} images, page size {page_size}")
        populate_photos_db(new_photos, container, db)

        photos |= set(new_photos)
        ids |= set(photo.id for photo in new_photos)

        if len(new_photos) < page_size:
            break
        page += 1
        # pause to avoid clampdown by Flickr?
        pause = random.random() * 15
        eprint(f"pause {pause:.2f}s")
        time.sleep(pause)

    eprint(len(photos), "photos")
    return photos

def classify_photos(photos):
    orphans = set()
    rest = set()
    errors = set()
    n = timeouts = 0
    for photo in photos:
        n += 1
        if n % 25 == 0:
            eprint("... photos:", len(rest),
                   "orphans:", len(orphans),
                   "errors:", len(errors))
            # pause to avoid clampdown by Flickr?
            pause = random.random() * 15
            eprint(f"pause {pause:.2f}s {n}")
            time.sleep(pause)
        try:
            album_context = call_flickr(photo.getAllContexts)
            album_context = album_context[0]
        except FlickrCallFailed as exc:
            if str(exc) == "timeout":
                timeouts += 1
                if timeouts >= 10:
                    eprint("Too many timeouts")
                    break
                continue
            eprint("error getting contexts for", photo, exc)
            errors.add(photo)
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
    eprint("photos:", len(rest),
           "orphans:", len(orphans),
           "errors:", len(errors))

    return orphans, errors, rest


def save_photos(photos, user, outputdir="."):
    if not photos:
        return
    eprint(f"saving {len(photos)} photos to {outputdir}")
    outputdir = Path(outputdir)
    outputdir.mkdir(parents=True, exist_ok=True)

    n = 0
    for photo in photos:
        n += 1
        if n % 25 == 0:
            # pause to avoid clampdown by Flickr?
            pause = random.random() * 15
            eprint(f"pause {pause:.2f}s {n}")
            time.sleep(pause)
        if n % 100 == 0:
            eprint("... photos:", n)
        filename = outputdir.joinpath(f"{user.id}.{photo.id}.jpg")
        try:
            call_flickr(photo.save, filename, size_label="Original")
        except FlickrCallFailed as exc:
            eprint(f"error saving {filename} ({exc})")
            eprint("Pause 15s")
            time.sleep(15)

def delete_photos(photos):
    if not photos:
        return

    yn = input(f"Delete {len(photos)} photos (y/n)? ")
    if not yn or yn.lower()[0] != "y":
        eprint("Delete not confirmed.")
        return

    n = 0
    for photo in photos:
        n += 1
        if n % 25 == 0:
            # pause to avoid clampdown by Flickr?
            pause = random.random() * 15
            eprint(f"pause {pause:.2f}s {n}")
            time.sleep(pause)
        if n % 100 == 0:
            eprint("... photos:", n)
        try:
            call_flickr(photo.delete)
        except FlickrCallFailed as exc:
            eprint(f"error deleting photo {photo.id} ({exc})")
            eprint("Pause 15s")
            time.sleep(15)


def flickr_login(username):
    with open("flickr_keys.toml", "rb") as keyfile:
        keys = tomllib.load(keyfile)
    flickr.set_keys(api_key=keys["API_KEY"], api_secret=keys["API_SECRET"])
    flickr.set_auth_handler("./flickr_auth")
    flickr.enable_cache()
    return call_flickr(flickr.Person.findByUserName, username)


def get_album(album_name, user, db):
    albums = user.getPhotosets()

    # Take the opportunity to populate albums table
    cur = db.cursor()
    cur.execute("begin")
    for album in albums:
        n = cur.execute(
            "select count(*) from albums"
            "  where id = ?", (album.id,)).fetchone()[0]
        if n == 0:
            url = (f"https://www.flickr.com/photos/"
                f"{album.owner}/albums/{album.id}")
            cur.execute(
                "insert into albums"
                "  (id, title, created, url)"
                "    VALUES"
                "  (?, ?, ?, ?)",
                (album.id, album.title, album.date_create, url))
            eprint(f"Inserted {album} in db")
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
    parser.add_argument("--delete-all", dest="deleteall", default=False,
                        action="store_true",
                        help="if true delete all photos, not just orphans")
    parser.add_argument("--delete", dest="delete", action="store_true",
                        help="delete orphaned photos", default=False)
    parser.add_argument("-m", "--maxphotos", dest="maxphotos", type=int,
                        help="max # of photos to download", default=0)
    parser.add_argument("-u", "--user", dest="user", required=True, help="Flickr username")
    parser.add_argument("-d", "--database", help="SQLite3 database filename",
                        default=":memory:")
    parser.add_argument("-a", "--album", help="Album to download",
                        default="Auto Upload")
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
          url TEXT,
          created INTEGER,
          taken INTEGER
        )""")

        conn.execute("""
        create table albums (
          id TEXT PRIMARY_KEY,
          title TEXT,
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

    album = get_album(args.album, user, db)
    photos = load_photos(album, maxphotos=args.maxphotos, db=db)

    orphans, errors, rest = classify_photos(photos)
    eprint(f"{len(orphans)} orphans")
    eprint(f"{len(errors)} uncategorized due to errors")
    eprint(f"{len(rest)} everything else")

    if args.save is not None:
        eprint("saving photos to", args.save)
        save_photos(orphans, user, args.save)
        save_photos(errors, user, args.save)
        save_photos(rest, user, args.save)

    if args.delete:
        delete_photos(orphans)
        if args.deleteall:
            delete_photos(errors)
            delete_photos(rest)

    return 0


if __name__ == "__main__":
    sys.exit(main())
