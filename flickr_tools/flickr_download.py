#!/usr/bin/env python

"""
Download orphaned photos from Flickr.
"""

import argparse
from pathlib import Path
import random
import sqlite3
import sys
import time
import tomllib
import traceback

import dateutil.parser
import flickr_api as flickr
import regex as re
import requests

def call_flickr_method(method, *args, **kwds):
    try:
        return (method(*args, **kwds), None)
    except flickr.FlickrError as exc:
        errmsg = re.sub("<html[^>]*>.*</html>",
            "<html> ... (elided) ...</html>",
            str(exc), flags=re.DOTALL)
        traceback.print_tb()
        print("Pause 15s")
        time.sleep(15)
        return (None, errmsg)
    except requests.Timeout:
        traceback.print_tb()
        return (None, "timeout")

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
    n = nerrs = timeouts = 0
    while True:
        page_size = 500 if maxphotos == 0 else min(500, maxphotos)

        (new_photos, failure) = call_flickr_method(container.getPhotos,
                                                   per_page=page_size, page=page)
        if failure == "timeout":
            timeouts += 1
            if timeouts >= 10:
                print("Too many timeouts")
                break
            continue
        elif failure is not None:
            nerrs += 1
            print(f"Error: {failure}")
            if nerrs >= 10:
                print("Too many errors, giving up")
                break
            continue

        populate_photos_db(new_photos, container, db)

        photos |= set(new_photos)
        ids |= set(photo.id for photo in new_photos)
        if len(ids) == n:
            break
        n = len(ids)
        print("n:", n, "page:", page)
        if maxphotos and n >= maxphotos:
            break
        page += 1
        # pause to avoid clampdown by Flickr?
        pause = random.random() * 15
        print(f"pause {pause:.2f}s")
        time.sleep(pause)

    print(n, "photos")
    return photos

def classify_photos(photos):
    orphans = set()
    rest = set()
    errors = set()
    n = timeouts = 0
    for photo in photos:
        n += 1
        if n % 25 == 0:
            # pause to avoid clampdown by Flickr?
            pause = random.random() * 15
            print(f"pause {pause:.2f}s")
            time.sleep(pause)
        if n % 100 == 0:
            print("... photos:", n, "orphans:", len(orphans))
        (album_context, failure) = call_flickr_method(photo.getAllContexts)
        if failure is None:
            album_context = album_context[0]
        elif failure == "timeout":
            timeouts += 1
            if timeouts >= 10:
                print("Too many timeouts")
                break
            continue
        else:
            print("error getting contexts for", photo, failure)
            print("Pausing 15s")
            time.sleep(15)
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

    return orphans, errors, rest


def save_photos(photos, user, outputdir="."):
    if not photos:
        return
    print(f"saving {len(photos)} photos to {outputdir}")
    outputdir = Path(outputdir)
    outputdir.mkdir(parents=True, exist_ok=True)

    n = 0
    for photo in photos:
        n += 1
        if n % 25 == 0:
            # pause to avoid clampdown by Flickr?
            pause = random.random() * 15
            print(f"pause {pause:.2f}s")
            time.sleep(pause)
        if n % 100 == 0:
            print("... photos:", n)
        filename = outputdir.joinpath(f"{user.id}.{photo.id}.jpg")
        (_, failure) = call_flickr_method(photo.save, filename, size_label="Original")
        if failure:
            print(f"error saving {filename} ({failure})")
            print("Pause 15s")
            time.sleep(15)

def delete_photos(photos):
    yn = input(f"Delete {len(photos)} photos (y/n)? ")
    if not yn or yn.lower()[0] != "y":
        print("Delete not confirmed.")
        return

    n = 0
    for photo in photos:
        n += 1
        if n % 25 == 0:
            # pause to avoid clampdown by Flickr?
            pause = random.random() * 15
            print(f"pause {pause:.2f}s")
            time.sleep(pause)
        if n % 100 == 0:
            print("... photos:", n)
        (_, failure) = call_flickr_method(photo.delete)
        if failure is not None:
            print(f"error deleting photo {photo.id} ({failure})")
            print("Pause 15s")
            time.sleep(15)


def flickr_login(username):
    with open("flickr_keys.toml", "rb") as keyfile:
        keys = tomllib.load(keyfile)
    flickr.set_keys(api_key=keys["API_KEY"], api_secret=keys["API_SECRET"])
    flickr.set_auth_handler("./flickr_auth")
    flickr.enable_cache()
    return flickr.Person.findByUserName(username)


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
    db.commit()

    return [album for album in albums if album.title == album_name][0]


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--save", dest="save",
                        help="save orphaned photos to this dir")
    parser.add_argument("--save-all", dest="saveall", default=False,
                        action="store_true",
                        help="if true save all photos, not just orphans")
    parser.add_argument("--delete", dest="delete", action="store_true",
                        help="delete orphaned photos", default=False)
    parser.add_argument("-m", "--maxphotos", dest="maxphotos",
                        type=int,
                        help="max # of photos to download", default=0)
    parser.add_argument("-u", "--user", dest="user", required=True,
                        help="Flickr username")
    parser.add_argument("-d", "--database", help="SQLite3 database filename",
                        default=":memory:")
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
    args = parse_args()
    user = flickr_login(args.user)

    db = get_db_connection(args.database)

    # We're currently only interested in identifying photos which have been
    # uploaded but not added to other albums. Album name should be a command
    # line arg.
    auto_upload = get_album("Auto Upload", user, db)
    photos = load_photos(auto_upload, maxphotos=args.maxphotos,
        db=db)

    orphans, errors, rest = classify_photos(photos)
    print(f"{len(orphans)} orphans")
    print(f"{len(errors)} uncategorized due to errors")
    print(f"{len(rest)} everything else")

    if args.save is not None:
        save_photos(orphans, user, args.save)
        save_photos(errors, user, args.save)
        if args.saveall:
            save_photos(rest, user, args.save)

    if args.delete:
        delete_photos(orphans)

    return 0


if __name__ == "__main__":
    sys.exit(main())
