import time, logging, praw, sqlite3, reconfig
import urllib.request
import numpy as np
import cv2 as cv
import prawcore.exceptions as ex


logging.captureWarnings(True)
logging.basicConfig(filename='repost.log', format='%(asctime)s %(levelname)s:%(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)


FETCH_QUERY = 'SELECT sids, hash FROM hashes WHERE h1=? OR h2=? OR h3=? OR h4=? OR h5=?'
FIND_QUERY = 'SELECT sids FROM hashes WHERE hash=?'
INSERT_QUERY = 'INSERT INTO hashes(hash, sids, h1, h2, h3, h4, h5) VALUES(?, ?, ?, ?, ?, ?, ?)'
EDIT_QUERY = 'UPDATE hashes SET sids=? WHERE hash=?'

INFO_QUERY = 'SELECT title, author, utctime, re FROM submissions WHERE sid=?'
INSERT_INFO_QUERY = 'INSERT INTO submissions(sid, author, utctime, title, re) VALUES(?, ?, ?, ?, 0)'

REDDIT_SPECIAL_CHARS = ('*', '_', '~', '^', '`', '>!')


# takes a path to an image file and returns a difference hash for the image
def hash(image):
    if image is None:
        return None
    image = cv.cvtColor(image, cv.COLOR_BGR2GRAY)
    resized = cv.resize(image, (9, 8))
    if np.all(resized == resized[0,0]):
        return None
    diff = resized[:, 1:] > resized [:, :-1]
    # the hash is returned as an array of 64 bits
    return diff.astype(int).flatten()


# takes 2 arrays and calculates the Hamming Distance between them
def hammingDistance(array1, array2):
    return np.count_nonzero(array1 != array2)


# convert buffer directly to opencv image format in memory
def get_opencv_img_from_buffer(buffer):
    bytes_as_np_array = np.frombuffer(buffer.read(), dtype=np.uint8)
    return cv.imdecode(bytes_as_np_array, cv.IMREAD_COLOR)


# turn a hash string into 5 separate integers for storage in the DB
def hash_string_to_ints(s):
    ssplit = (s[:13], s[13:26], s[26:39], s[39:52], s[52:])
    return tuple(map(lambda x: int(x, 2), ssplit))

    
def main():
    # Reddit connection
    reddit = praw.Reddit(reconfig.user)
    sub = reddit.subreddit(reconfig.subreddit)
    
    #DB connection
    conn = sqlite3.connect(reconfig.db_path)
    c = conn.cursor()
    
    while True:
        try:
            for submission in sub.stream.submissions(skip_existing=True):
                if submission.is_self:
                    continue
                
                if submission.url.lower().endswith(('.jpg', '.png')):
                    url = submission.url
                else:
                    url = submission.thumbnail
                    
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Python3.7.3 (Linux4.19.50) repostbot1.0'})
                    response = urllib.request.urlopen(req)
                except Exception as e:
                    logging.exception('Request Exception')
                    continue
                
                img = get_opencv_img_from_buffer(response)
                hash_array = hash(img)
                if hash_array is None:
                    continue
                hash_string = np.array2string(hash_array, separator='')[1:-1]
                hash_ints = hash_string_to_ints(hash_string)
                sid = submission.id
                
                c.execute(FETCH_QUERY, hash_ints)
                rows = c.fetchall()
                
                matches = []
                for row in rows:
                    a = np.array([1 if digit=='1' else 0 for digit in row[1]])
                    differences = hammingDistance(a, hash_array)
                    if differences <= 4:
                        for submission_id in row[0].split(','):
                            matches.append((differences, submission_id))
                            
                matches = sorted(matches, key=lambda tup: tup[0])
                duplicate = False
                if len(matches) > 0:
                    reply_string = 'Possible repost of:\n\n| Submission | Author | Age | :) |\n| :- | :- | -: | :-: |'
                    for diff, match in matches[:10]:
                        if match == sid:
                            duplicate = True
                            break
                        c.execute(INFO_QUERY, (match,))
                        info = c.fetchone()
                        time_diff = time.time() - info[2]
                        age = (f"{int(time_diff/86400)}  days" if time_diff >= 86400 else f"{int(time_diff/3600)} hours")
                        title = info[0].replace('\\', '').replace('|', '&#124;').replace('[', '&#91;').replace(']', '&#93;')
                        for char in REDDIT_SPECIAL_CHARS:
                            title = title.replace(char, f"\\{char}")
                        reply_string += f"\n| [{title}](https://redd.it/{match}) | {info[1]} | {age} | {':)' if info[3] else ''} |"
                    if duplicate:
                        continue
                    reply_comment = submission.reply(reply_string)
                    reply_comment.mod.remove()
                    submission.report("Possible Repost - check comments")
                    
                c.execute(INSERT_INFO_QUERY, (sid, submission.author.name, submission.created_utc, submission.title))
                conn.commit()
                
                c.execute(FIND_QUERY, (hash_string,))
                exists = c.fetchone()
                if exists:
                    c.execute(EDIT_QUERY, (exists[0] + f",{sid}", hash_string))
                else:
                    c.execute(INSERT_QUERY, (hash_string, sid) + hash_ints)
                conn.commit()

        except KeyboardInterrupt:
            break
        except (ex.RequestException, ex.ResponseException) as e:
            logging.error(e)
            time.sleep(10)
            continue
        except Exception as e:
            logging.exception('Unexpected Exception')
            continue


if __name__ == '__main__':  
    main()
