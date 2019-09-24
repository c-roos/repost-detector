# repost-detector
A bot for detecting image reposts on Reddit

This bot monitors new submissions to a subreddit, downloads submitted images, generates hashes from them, and compares the hashes to previous hashes to see if the images have been posted before.

Currently stores hashes in a pickled dictionary, which is less than ideal, but I was waiting for piwheels to release an opencv package for python 3.4 so I could move the bot to my Pi and run it with SQLite. The package recently became available, so I'll be moving the bot over soon.
