# twitter-delete

A basic script to delete all your tweets.

It uses python and Selenium to drive a local Firefox browser to do the work. (No twitter API usage.)

## How to use:

1. Get a backup of your tweets.

2. Put your username and password in a file called "credentials.txt" looking something like this:

```
username: tweetyacount
password: seekrit
```

3. Put that "credentials.txt" and "tweets.js" from your backup into the same directory

4. Then run the script. And watch the tweets slowly go away

```
./delete.py
```

Have fun!

Expect Twitter to slow-roll your connection or throw a few errors at you. It's awful curious how that happens if you've been deleting a few hundred tweets.