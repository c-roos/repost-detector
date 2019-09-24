import pickle, praw, config
import urllib.request
import numpy as np
import cv2 as cv


# takes an integer and returns a list of bits
def intToBitList(n, size):
    return [1 if digit=='1' else 0 for digit in f"{n:0{size}b}"]


# takes an array of bits and return the integer representation
def bitArrayToInt(a):
    out = 0
    for bit in a:
        out = (out << 1) | bit
    return out

    
# takes a row of 11 integers from the database and combines them into a list of 64 bits
def combineRow(row):
    l = []
    for integer in row[:-1]:
        l.extend(intToBitList(integer, 6))
    l.extend(intToBitList(row[-1], 4))
    return l

    
# takes an array of 64 bits and splits it into a list of 11 integers to store in the database (10x6, 1x4 bits)
def splitBitArray(a):
    integers = []
    for i in range(0, 60, 6):
        integers.append(bitArrayToInt(a[i:i+6]))
    integers.append(bitArrayToInt(a[60:]))
    return integers

    
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
    
    
def main():
    # Reddit connection
    reddit = praw.Reddit(config.user)
    sub = reddit.subreddit(config.subreddit)
    
    # load stored hashes
    hashes = pickle.load(open('hashes.p', 'rb'))
    i = 0
    
    for submission in sub.stream.submissions(skip_existing=True):
        i = (i+1)%10
        if submission.is_self:
            continue
        
        if submission.url.endswith(('.jpg', '.png')):
            url = submission.url
        else:
            url = submission.thumbnail
            
        try:
            response = urllib.request.urlopen(url)
        except:
            continue
        
        download = response.read()
        f_name = 'temp' + url[-4:]
        with open(f_name, 'wb') as f:
            f.write(download)
        img = cv.imread(f_name)
        hash_array = hash(img)
        if hash_array is None:
            continue
        hash_string = np.array2string(hash_array, separator='')[1:-1]
        
        matches = []
        for key in hashes.keys():
            a = np.array([1 if digit=='1' else 0 for digit in key])
            differences = hammingDistance(a, hash_array)
            if differences <= 4:
                matches.extend(hashes[key])
        
        # I've had issues with reddit returning the same sumission multiple times
        # so I have to check for duplicates
        duplicate = False
        if len(matches) > 0:
            reply_string = 'Possible repost of:'
            for match in matches:
                if match == submission.id:
                    duplicate = True
                    break
                reply_string = reply_string + f"\n\nhttps://redd.it/{match}"
            if duplicate:
                continue
            reply_comment = submission.reply(reply_string)
            reply_comment.mod.remove()
            submission.report("Possible Repost: check comments")
        
        l = hashes.get(hash_string, [])
        l.append(submission.id)
        hashes[hash_string] = l
        
        # every 10 hashes, save the new ones
        # will move to an actual database soon
        if i == 9:
            pickle.dump(hashes, open('hashes.p', 'wb'))
        
    
if __name__ == '__main__':  
    main()