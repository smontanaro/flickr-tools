# Flickr Manipulation Notes #

The basic problem is the web interface to Flickr is abysmal. Not only
is Flickr slow, but you can't perform some basic queries, such as:

  * Return all images not in any album
  * Return all images only in Auto Uploads
  * Return all images in album 1 or album 2 (or ...)
  * Return all images before (or after)
  * Delete images matching certain constraints en mass

# Image Properties #

  * Image name
  * Image meta parameters (size, file type, privacy, etc)
  * Date - taken and uploaded
  * Album(s) containing a particular image

# Album Properties #

  * Return all images ...
  * or all images with certain properties (private, public, in other
    albums, ...)

# Flickr API #

I don't know if the Flickr API allows you to make all these queries.
If not, it might be worthwhile to consider querying each image for its
basic properties (containing albums, basic image parameters, privacy,
etc), then build a SQL database from the returned information. More
complex queries could be made locally, only falling back to the Flickr
API to manipulate individual images or albums.
