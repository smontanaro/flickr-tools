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

The wheels began to fall off after Flickr was [purchased by SmugMug in
2018](https://en.wikipedia.org/wiki/Flickr).  Despite any professed
"love" for Flickr, as far as I can tell the only changes have been to
cap the free tier at 1,000 photos and start raising the price for the
Pro tier.

I had the Flickr auto uploader enabled, which was handy, but at the
time the free tier max changed, I had 6,000 or so photos in my
account, many — but far from most — organized into albums.  Most were
only in the Auto Upload folder.  They didn't even offer tools to help
Flickr users migrate to SmugMug or selectively filter photos.  I had
no way to easily find uncategorized photos.  I would have just had to
work through them one-by-one, checking to see if each photo was in
another album or not.  If you didn't get down to the free tier max by
a certain date, Flickr was going start deleting photos, oldest first.
They offered no indication that they would be selective.  I began
grumbling privately about it, but the lack of any useful tools to get
me even close to 1,000 photos forced me to just pony up for Pro.
Looking at the above Wikipedia link, I see that they changed their
policy about deletion.  I never recall hearing about that.  I guess
not telling me was a boost to the bottom line.

A couple years passed.  I got the latest bill a week or so ago, $130+
for two years of Pro.  That was the straw that broke this camel's
back, so I started getting serious about creating a tool to help me
whittle down my collection.  That has turned into this piece of junk.
**Seriously, don't use this as a model of good programming practice
(Python or otherwise), or the correct way to use Flickr's (flaky)
API.** Did I mention their API is kinda flaky?

# Running the download app #

If you run the `flickr-download` with the `--help` flag you will get a
bit of help about the command line flags. I will perhaps expand on
that in the future, but for now, if you need more, Read the Source,
Luke.

There is a certain amount of work to do before you can run the app for
the first time. It can be confusing, especially for someone (like me)
who's not well-versed in the ins and outs of OAUTH.  Fortunately, you
only need to jump through these hoops once.

## Keys & Secrets ##

The first thing you need to do is generate `API_KEY` and `API_SECRET`
tokens.  Follow the directions on this Flickr page:

https://www.flickr.com/services/api/keys

Once you have them, create a file in your current directory named
`flickr_keys.toml`.  (This filename is currently hard-coded.)  It will
have this format:

```
API_KEY = "<YOUR KEY HERE>"
API_SECRET = "<YOUR SECRET HERE>"
```

**Don't check this into your git repo!**

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

**Don't check this into your git repo!**

Given that these files are hard-coded into the `flickr-download` app
without any directory info, you currentl must keep them in the same
directory and run the app from that directory.  Someday I might get
around to changing that.
