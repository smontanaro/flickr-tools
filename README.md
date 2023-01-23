# Flickr Tools #

This is a crude tool originally written to download orphaned Flickr
photos — photos which show up in no albums, except possibly Auto
Upload.  I've added a few "features," but nothing dramatic.  Don't
rely on it as a prototype for other Flickr apps.

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
