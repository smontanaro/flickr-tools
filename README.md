# Flickr Tools #

This is a crude tool originally written to download orphaned Flickr
photos — photos which show up in no albums, except possibly Auto
Upload.  I've added a few "features," but nothing dramatic.  Don't
rely on it as a prototype for other Flickr apps.

## Motivation ##

I've been a Flickr user since 2007. It was free, speed was okay, it
was easy to collect photos in albums, and it was easy to share photos
by reference in common forums in which I participate, most notably
[bikeforums.net](bikeforums.net),
[forums.thepaceline.net](forums.thepaceline.net), and
[velocipedesalon.com](velocipedesalon.com).

The wheels began to fall off as far as I was concerned after Flickr
was [purchased by SmugMug in
2018](https://en.wikipedia.org/wiki/Flickr).  Despite any professed
"love" for Flickr, as far as I can tell the only changes have been to
cap the free tier at 1,000 photos (it had been 1TB, roughly 375,000
photos based on my average photo size) and start raising the price for
the Pro tier.

I had the Flickr auto uploader enabled, which was handy, but at the
time the free tier limit changed, I had 6,000 or so photos in my
account, many — but far from most — organized into albums.  Most were
only in the Auto Upload folder.  They didn't offer tools to help users
semi-intelligently find photos to delete or to migrate to SmugMug. I
had no way to easily find uncategorized photos.  I would have just had
to work through the photos on the web interface one-by-one, checking
to see if a photo had been added to an album I'd created or not.  If
you didn't get down to the free tier max by a certain date, Flickr was
going start deleting photos, oldest first.  They offered no indication
that they would be selective.  I began grumbling privately about it,
but the lack of any useful tools to even get close to 1,000 photos
forced me to just pony up for Pro.  Looking at the above Wikipedia
link, I see that they waffled about the changes to the free tier.  I
don't recall ever hearing about that.  I guess not telling me was a
boost to the bottom line.

A couple years passed.  I got the latest bill a week or so ago, $130+
for two years of Pro.  That was the straw that broke this particular
camel's back, so I started getting serious about creating a tool to
help me whittle down my collection.  That has turned into this piece
of junk.  **Seriously, don't use this as a model of good programming
practice (Python or otherwise), or the correct way to use Flickr's
(flaky) API.** Did I mention their API is kinda flaky? "Connection
reset by peer" is my new archnemesis.

# Running the download app #

If you run the `flickr-download` with the `--help` flag you will get a
bit of help about the command line flags. I will perhaps expand on
that in the future, but for now, if you need more, Read the Source,
Luke.

You must do a certain amount of work before you can run the app for
the first time. It can be confusing, especially for someone (like me)
who's not well-versed in the ins and outs of OAUTH.  Fortunately, the
[python-flickr-api package](https://pypi.org/project/flickr-api/)
hides most of that and you only need to jump through these hoops once.

## Keys & Secrets ##

The first thing you need to do is generate `API_KEY` and `API_SECRET`
tokens.  Follow the directions on this Flickr page:

https://www.flickr.com/services/api/keys

Once you have them, create a file in your current directory named
`flickr_keys.toml`.  (This filename is currently hard-coded.)  It must
have this format:

```
API_KEY = "<YOUR KEY HERE>"
API_SECRET = "<YOUR SECRET HERE>"
```

**Don't check this file into your git repo!**

Now you need to get authorized.  You can authorize yourself for
"read", "write", or "delete" permissions, each one being more
potentially damaging to your photo collection than the one before it.
Follow the directions here:

https://github.com/alexis-mignon/python-flickr-api/wiki/Flickr-API-Keys-and-Authentication#authentication

When you save to a file, choose `flickr_auth` as your filename. (This
filename is currently hard-coded.) It will have this format:

```
<REALLY LONG HEX STRING>
<NOT NEARLY AS LONG HEX STRING>
```

**Don't check this file into your git repo!**

Given that these files are hard-coded into the `flickr-download` app
without any directory info, you currently must keep them in the same
directory and run the app from that directory.  Someday I might get
around to changing that.

## Command Line ##

At minimum, you need to give the `--user` argument so you can
login. By default, it will fetch the user's photos.  You can also
give the `--album` argument to restrict view to a particular album.

When first written, the goal was to identify and download "orphan"
photos, those which were in no albums or in just the Auto Upload
album.  The goal was to allow download and deletion of such orphan
photos to reduce the user's Flickr footprint.  Accordingly, photo
deletion is split into two parts, `--delete-orphans` and
`--delete-all` The latter is subservient to the former (you need to
delete orphan images if you want to delete non-orphan images).  This
is probably not the best way to do things. It's just the current state
of affairs.  If any photos are candidates for deletion, the program
prompts for confirmation.

Generally speaking, you will want to save (`--save`) the photos, but
it's not required.  Similarly, you can choose to specify a SQLite3
database file, but it's not required.

For debugging purposes, you can use `--maxphotos` to only process a
subset of available photos.  The `--verbose` flag produces plenty of
output.  Without it, the program is basically silent.

### Examples ###

  * Download the Auto Upload album, save its photos, and delete those
    which are orphans from Flickr:

    `flickr_download --user you --save auto-upload --album 'Auto Upload' --delete-orphans`

  * Download an album named `My Bikes`, but don't save or delete
    anything, just save the details to a SQLite3 database named
    `flickr.db`:

    `flickr_download --user you --album 'My Bikes' --database flickr.db`
