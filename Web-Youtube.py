from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from pathlib import Path
from time import sleep
import pandas as pd
import requests
import isodate
import json
import math
import sys
from youtube_transcript_api import YouTubeTranscriptApi
# imported files
from progress_bar import printProgressBar
from getCommandLine import getCommands, supportedStyles


# parts and item_id will have to be properly formmated
def YT_json(directory, parts, item_id, api_key, new_Page_Token=''):  # add try except block for request timeouts
	url = f'https://www.googleapis.com/youtube/v3/{directory}?{parts}&{item_id}{api_key}'
	if new_Page_Token:
		url += f'&pageToken={new_Page_Token}'
	if directory != 'videos' and directory != 'channels':
		url += '&maxResults=100'
	return requests.get(url).json()

# combines all comment meta data into a single array
def commentData(item, cData, parent):
	comment = [item['id'], cData['textOriginal'], cData['authorDisplayName'], cData['authorChannelUrl'], cData['likeCount'], cData['publishedAt'], cData['updatedAt'], parent]
	return comment

# get commentThreads and comment replies from the video 
def getComments(d_type, vid_type, api_key, parts='part=snippet', parent='id'):
	first_run, is_thread = True, d_type == 'Thread'
	if is_thread:
		parts, parent = f'{parts},replies', 'id'
	next_pg = ''
	all_comments, comments_with_replies, json_data = [], [], []
	while first_run:  # or 'nextPageToken' in json_comments:
		first_run = False
		json_comments = YT_json(f'comment{d_type}s', parts, vid_type, api_key, next_pg)
		if 'items' in json_comments:
			json_data += json_comments['items']
		else: 
			print(json_comments)  # prints errors -> TRY to handle better
		if 'nextPageToken' in json_comments:
			first_run = True
			next_pg = json_comments['nextPageToken']
	for item in json_data:
		cData = item['snippet']  # comments
		if is_thread: 
			cData = item['snippet']['topLevelComment']['snippet']  # commentThreads
			reply_num = int(item['snippet']['totalReplyCount'])
			if reply_num < 6 and 'replies' in item:  # add comments (available w/ response)
				for n_item in item['replies']['comments']:
					all_comments.append(commentData(n_item, n_item['snippet'], item[parent]))
				#all_cmnts = [cmntData(elm, elm['snippet'], item[parent]) for elm in item['replies']['comments']]
			elif 'replies' in item:
				comments_with_replies.append(item['id']) 
		all_comments.append(commentData(item, cData, item[parent]))
	return all_comments, comments_with_replies

# youtube API to get more specific information about the video
def youtubeAPI(video_id, api_key, data_dict, data_opt):
	json_parts = 'part=snippet,statistics,contentDetails,topicDetails'
	json_response = YT_json('videos', json_parts, f'&id={video_id}', api_key)
	allComments = []
	data_dict['video_url'] = f'https://www.youtube.com/watch?v={video_id}'
	
	if 'pageInfo' not in json_response:  # JSON Error is Quota Filled 
		raise ValueError
	if int(json_response['pageInfo']['totalResults']) > 0:  # for deleted & priv vids in playlists
		statistics = json_response['items'][0]['statistics']
		data_dict['views'] = statistics['viewCount'] if 'viewCount' in statistics else 0 # streamed
		data_dict['likes'] = statistics['likeCount'] if 'likeCount' in statistics else 0
		data_dict['dislikes'] = statistics['dislikeCount'] if 'dislikeCount' in statistics else 0
		data_dict['favorites'] = statistics['favoriteCount']
		if 'commentCount' in statistics and int(statistics['commentCount']) > 0:
			data_dict['comment_number'] = statistics['commentCount']
			if data_opt['cmtOn']:  # cycle through the various comments on the video
				commentSetup = ['comment_id', 'comment', 'comment_author', 'comment_author_url', 'comment_likes', 'comment_published', 'comment_updated_time', 'parent_comment']
				allComments.append(commentSetup)
				temp_data, c_replies = getComments('Thread', f'videoId={video_id}',  api_key)
				allComments += temp_data
				comments_with_replies = c_replies
				# comments that have more replies than can obtain via thread replies
				for comment_id in comments_with_replies:
  					temp_data, _ = getComments('', f'parentId={comment_id}', api_key)
  					allComments += temp_data
		else:
			data_dict['comment_number'] = 0
		snippet = json_response['items'][0]['snippet']
		data_dict['video_published'] = snippet['publishedAt']
		data_dict['description'] = snippet['description']
		if 'maxres' in snippet['thumbnails']:
			data_dict['max_thumbnail'] = snippet['thumbnails']['maxres']['url']
		elif 'standard' in snippet['thumbnails']:
			data_dict['max_thumbnail'] = snippet['thumbnails']['standard']['url']
		elif 'high' in snippet['thumbnails']:
			data_dict['max_thumbnail'] = snippet['thumbnails']['high']['url']
		elif 'medium' in snippet['thumbnails']:
			data_dict['max_thumbnail'] = snippet['thumbnails']['medium']['url']
		elif 'default' in snippet['thumbnails']:
			data_dict['max_thumbnail'] = snippet['thumbnails']['default']['url']
		if 'tags' in snippet:
			data_dict['video_tags'] = snippet['tags']
		data_dict['category_Id'] = snippet['categoryId']
		video_duration = json_response['items'][0]['contentDetails']['duration']
		if data_opt['secOn']:
			data_dict['seconds_duration'] = isodate.parse_duration(video_duration).total_seconds()
		else:
			data_dict['ISO_8601_duration'] = video_duration
		if 'topicDetails' in json_response['items'][0]:
			data_dict['video_topics'] = json_response['items'][0]['topicDetails']['topicCategories']

	return data_dict, allComments


def getLinkID(yt_link, splitThis):
	meta = yt_link.split('?')
	if '&' in meta[-1]:
		meta = [string for string in meta[-1].split('&') if splitThis in string]
	youtube_id = meta[-1].split(splitThis)[-1]
	return youtube_id

# gets the subtitles / captions from the video that's already generated
def getCaptions(vid_id):
	try:
		captions = YouTubeTranscriptApi.get_transcript(vid_id)
	except:
		return ""
	totalCaptions = " ".join([item['text'] for item in captions])
	return totalCaptions

# main function to get all of the data from the videos 
def videoData(videos, tagName, tag, tagName_two, api_key, data_opt, splitby):
	for video in videos:
		data_dict = {}
		# get title
		data_dict['title'] = video.find('a', {'id': tagName})['title']  # was a 'span'
		# get video url + use id for youtube API
		vid_id = getLinkID(video.find('a', {tag: tagName_two})['href'], splitby)
		if data_opt['subOn']:
			data_dict['captions'] = getCaptions(vid_id)
		try:
			data_dict, data_dict['comments'] = youtubeAPI(vid_id, api_key, data_dict, data_opt)
		except ValueError: # testing for exceeding quota
			data_dict['video_url'] = 'https://www.youtube.com/watch?v=' + vid_id
			master_list.append(data_dict)
			print('\nquota reached')
			break
		master_list.append(data_dict)
		printProgressBar(videos.index(video) + 1, len(videos), 'Processing Videos:', length=50)
	return master_list


if __name__ == "__main__":
	# using getopt to get the commands for the program to run with
	yt_link, api_key, data_opt = getCommands() # data_opt = [cmtOn, subOn, secOn]
	api_key = '&key=' + api_key
	all_links = [x for x in yt_link.split(' ') if "youtube" in x]

	for yt_link in all_links: # for multiple links inserted
		print(yt_link, '')
		scroll_amnt = 50  # arbitrary number for homepage/search -- user insert number to override?
		single_video = False
		chrome_options = Options()
		chrome_options.add_argument("--headless")
		driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

		title, title_id = '', 'video-title'  # default is for channels
		if any(x in yt_link for x in ['/user/', '/channel/', '/c/']):  # Channel
			split_link = yt_link.split('/')
			user_id = split_link[-2] if 'videos' in yt_link else split_link[-1]
			user_or_channel = f'&forUsername={user_id}' if '/user/' in yt_link else '&id='
			if '/user/' not in yt_link:
				driver.get(yt_link)
				channel = driver.find_element_by_xpath('/html/body/link[1]').get_attribute('href')
				user_or_channel += getLinkID(channel, '/')
			json_response = YT_json('channels', 'part=id,statistics', user_or_channel, api_key)
			scroll_amnt = int(int(json_response['items'][0]['statistics']['videoCount']) / 30) + 1
			driver.get(f'https://www.youtube.com/{split_link[3]}/{user_id}/videos')  # update channel
			title = driver.find_element_by_xpath('//*[@id="text-container"]').text + '.csv'
		elif 'list=' in yt_link:  # Playlists - if its a video in a playlist or the full playlist
			playlist_id = getLinkID(yt_link, 'list=')
			driver.get(f'https://www.youtube.com/playlist?list={playlist_id}')
			title = driver.find_element_by_xpath('//*[@id="title"]/yt-formatted-string/a').text + '.csv'
			vids = driver.find_element_by_xpath('//*[@id="stats"]/yt-formatted-string[1]/span[1]').text
			scroll_amnt = math.ceil(int(vids) / 100) + 1
		elif '?' not in yt_link:  # YouTube Homepage
			title, title_id = 'YouTube Homepage.csv', 'video-title-link'
			driver.get(yt_link)
		elif 'v=' in yt_link:  # single YouTube video
			scroll_amnt = 0
			single_video = True
			driver.get(yt_link)
		elif 'search_query' in yt_link:  # if using search bar
			driver.get(yt_link)
			meta = yt_link.split('search_query=')[1]
			if '&' in meta:  # for extra commands tacked on
				meta = meta.split('&')[0]
			title = meta.replace('+', ' ') + '.csv'
		else:  # improper usage
			print('\nThe entered youtube link is incompatible with the program')
			driver.close()
			supportedStyles()
		
		for i in range(scroll_amnt):  # scroll to the bottom of the youtube page
			printProgressBar(i + 1, scroll_amnt, 'Navigating Youtube:', length=50)
			driver.find_element_by_tag_name('body').send_keys(Keys.END)
			sleep(3)

		html = driver.page_source
		soup = BeautifulSoup(html, 'html.parser')
		master_list = []
		if 'list=' not in yt_link and not single_video:  # channel, homepage, and search
			videos = soup.find_all('div', {'id': 'dismissible'})
			videos = [x for x in videos if ('ytd-shelf-renderer' not in x['class'] and 'ytd-compact-promoted-item-renderer' not in x['class'] and 'ytd-rich-shelf-renderer' not in x['class'])]
			master_list = videoData(videos, title_id, 'id', title_id, api_key, data_opt, 'v=')
		elif single_video:
			data_dict = {'title': soup.find('meta', {'name': 'title'})['content']}
			title = data_dict['title'] + '.csv'
			data_dict, temp_item = youtubeAPI(getLinkID(yt_link, '='), api_key, data_dict, data_opt)
			if data_opt['subOn']:
				data_dict['captions'] = getCaptions(getLinkID(yt_link, '='))
			if len(temp_item) == 0:  # no comments used -- merge into master list
				master_list.append(data_dict)
			for i in range(1, len(temp_item)):  # splitting up comments to their own row
				for j, elm in enumerate(temp_item[i]):
					data_dict[temp_item[0][j]] = elm.replace('\r', '\\r') if type(elm) == str else elm
				master_list.append(data_dict)
				data_dict = {}
		else:  # works for playlist
			playlist_videos = soup.find_all('div', {'id': 'contents'})[0]
			videos = playlist_videos.find_all('div', {'id': 'content'})
			master_list = videoData(videos, title_id, 'class', 'yt-simple-endpoint', api_key, data_opt, 'v=')


		print('')  # new line for downloaded file
		driver.close()
		# put data into a CSV file + download to downloads folder
		youtube_df = pd.DataFrame(master_list)
		youtube_df.to_csv(str(Path.home() / "Downloads/") + '/' + title, index=False)
		print('downloaded', title)
		
