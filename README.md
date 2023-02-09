# YouTube data scraper

To easily scrape any data from the youtube homepage, a youtube channel/user, search results, playlists, and a single video itself.
Requires Python 3.6+

## Installing
```bash
$ pip3 install -r requirements.txt
```

## Help Menu

```bash
$ python3 Web-Youtube.py -h
Works with: YouTube Homepage, youtube search, channel/user, video, and playlists


Usage: Web-Youtube.py [OPTIONS]
	--link		 	YouTube link(s)
	--api	 		Google/YouTube API key
	--comments		Get comments from YouTube videos
				   [turning on will increase program run time]
	--subtitles		Get subtitles from YouTube videos
	--durationseconds	Get seconds from YouTube video duration
	--version       	List version release
	--help          	This help menu

Example:
	Web-Youtube.py --link "[your_youtube_link(s)]" --api [your_api_key] --comments --subtitles --durationseconds

Supported YouTube Link Styles:
	https://www.youtube.com/
	https://www.youtube.com/results?search_query=valuetainment
	https://www.youtube.com/user/patrickbetdavid
	https://www.youtube.com/channel/UCGX7nGXpz-CmO_Arg-cgJ7A
	https://www.youtube.com/watch?v=Z2UmjJ2zQkg&list=PLFa0bDwXvBlDGFtce9u__1sBj6fgi21BE
	https://www.youtube.com/watch?v=x9dgZQsjR6s
	https://www.youtube.com/playlist?list=PLFa0bDwXvBlDGFtce9u__1sBj6fgi21BE
```


## Sample Output

```bash
$ python3 Web-Youtube.py --link "https://www.youtube.com/watch?v=x9dgZQsjR6s" --api 6d5f807e23db210bc254a28be2d6759a0f5f5d99 --comments

Navigating Youtube: |██████████████████████████████████████████████████| 100.0% 
Processing Videos: |██████████████████████████████████████████████████| 100.0% 
downloaded Art of War & Strategic Thinking for Entrepreneurs in 2020.csv
```


## Get your YouTube API Key

Video tutorial: https://www.youtube.com/watch?v=TE66McLMMEw

Medium tutorial: (follow steps 1-3 no need to install the module) https://medium.com/greyatom/youtube-data-in-python-6147160c5833
