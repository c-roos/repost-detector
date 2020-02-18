# repost-detector
A bot for detecting image reposts on Reddit

This bot monitors new submissions to a subreddit, downloads submitted images, generates hashes from them, and compares the hashes to previous hashes to see if the images have been posted before.


# How It Works
## Monitoring Submissions
Using the PRAW Reddit wrapper, the bot checks every new post made to the specified subreddit. If the post is an image, the bot downloads it, hashes it, and compares the hash to previous hashes stored in a SQLite database. If the hashes are too similar (a hamming distance of less than 5 seems to be a decent threshold), then the post is a potential repost. The bot then makes a comment listing the potential matches and reports the post so a human moderator can verify.

## Hashing
A 64 bit hash is generated for each image using the OpenCV library. This is done by first discarding the color information, then shrinking the image down to 9x8 pixels. From there, each pixel's brightness is compared to the one next to it, with each comparison yeilding a single bit in the hash value. Hash values are stored in a SQLite database along with some additional information on the associated reddit post.
