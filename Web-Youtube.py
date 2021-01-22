from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from progress_bar import printProgressBar
from getCommandLine import getCommands
from bs4 import BeautifulSoup
from pathlib import Path
from time import sleep
import pandas as pd
import requests
import json
import math
import sys
import re



# parts and item_id will have to be properly formmated
def YT_json(directory, parts, item_id, api_key, new_Page_Token=''):
	url = f'https://www.googleapis.com/youtube/v3/{directory}?{parts}&{item_id}{api_key}'
	if new_Page_Token:
		url += f'&pageToken={new_Page_Token}'
	elif directory != 'videos' and directory != 'channels':
		url += '&maxResults=100'

	return requests.get(url).json()

# youtube API to get more specific information about the video
def youtubeAPI(video_id, api_key, data_dict, commentsOn):
	json_parts = 'part=snippet,statistics,contentDetails,topicDetails'
	json_response = YT_json('videos', json_parts, f'&id={video_id}', api_key)
	allComments = []
	data_dict['video_url'] = 'https://www.youtube.com/watch?v=' + video_id
	# to deal with deleted and private videos in playlists (mainly)
	if json_response['pageInfo']['totalResults'] != 0:
		statistics = json_response['items'][0]['statistics']
		data_dict['views'] = statistics['viewCount']
		data_dict['likes'] = statistics['likeCount'] if 'likeCount' in statistics else 0
		data_dict['dislikes'] = statistics['dislikeCount'] if 'dislikeCount' in statistics else 0
		data_dict['favorites'] = statistics['favoriteCount']
		if 'commentCount' in statistics and int(statistics['commentCount']) > 0:
			data_dict['comment_number'] = statistics['commentCount']
			if commentsOn:  # cycle through the various comments on the video
				json_comments = YT_json('commentThreads', 'part=id,snippet,replies', f'videoId={video_id}', api_key)
				commentSetup = ['comment_id', 'comment', 'comment_author', 'comment_author_url', 'comment_likes', 'comment_published', 'comment_updated_time', 'parent_comment']
				allComments.append(commentSetup)
				next_pg = ''
				comments_with_replies = []
				first_run = True
				while first_run or 'nextPageToken' in json_comments:
					first_run = False
					for item in json_comments['items']:
						cData = item['snippet']['topLevelComment']['snippet']
						comment = [item['id'], cData['textOriginal'], cData['authorDisplayName'], cData['authorChannelUrl'], cData['likeCount'], cData['publishedAt'], cData['updatedAt'], item['snippet']['topLevelComment']['id']]
						allComments.append(comment)
						if int(item['snippet']['totalReplyCount']) > 0:
							comments_with_replies.append(item['id'])
					if 'nextPageToken' in json_comments:
						first_run = True
						next_pg = json_comments['nextPageToken']
						json_comments = YT_json('commentThreads', 'part=snippet,replies', f'videoId={video_id}', api_key, next_pg)
				for comment_id in comments_with_replies:
					json_comments = YT_json('comments', 'part=snippet', f'parentId={comment_id}', api_key)
					page_Total_Results = len(json_comments['items'])
					for i in range(page_Total_Results):
						cData = json_comments['items'][i]['snippet']
						comment = [json_comments['items'][i]['id'], cData['textOriginal'], cData['authorDisplayName'], cData['authorChannelUrl'], cData['likeCount'], cData['publishedAt'], cData['updatedAt'], cData['parentId']]
						allComments.append(comment)
						if i == page_Total_Results - 1 and 'nextPageToken' in json_comments:
							next_pg = json_comments['nextPageToken']
							json_comments = YT_json('comments', 'snippet', f'parentId={comment_id}', api_key, next_pg)
							i = 0
							page_Total_Results = len(json_comments['items'])
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
		data_dict['ISO_8601_duration'] = json_response['items'][0]['contentDetails']['duration']
		if 'topicDetails' in json_response['items'][0]:
			data_dict['video_topics'] = json_response['items'][0]['topicDetails']['topicCategories']

	return data_dict, allComments


def getIDFromLink(yt_link, splitThis):
	meta = yt_link.split('?')
	if '&' in meta[-1]:
		meta = [string for string in meta[-1].split('&') if splitThis in string]
	youtube_id = meta[-1].split(splitThis)[-1]
	return youtube_id

if __name__ == "__main__":
	# using getopt to get the commands for the program to run with
	yt_link, api_key, commentsOn = getCommands()
	api_key = '&key=' + api_key

	title = ''
	scroll_amnt = 50  # arbitrary number for homepage/search -- user insert number to override?
	single_video = False
	chrome_options = Options()
	chrome_options.add_argument("--headless")
	driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

	title_id = 'video-title'  # default is for channels
	if any(x in yt_link for x in ['/user/', '/channel/', '/c/']):  # Channel
		split_link = yt_link.split('/')
		user_id = split_link[-2] if 'videos' in yt_link else split_link[-1]
		user_or_channel = f'&forUsername={user_id}' if '/user/' in yt_link else '&id='
		if '/user/' not in yt_link:
			driver.get(yt_link)
			channel_name = driver.find_element_by_xpath('/html/body/link[1]').get_attribute('href')
			user_or_channel += getIDFromLink(channel_name, '/')
		json_response = YT_json('channels', 'part=id,statistics', user_or_channel, api_key)
		scroll_amnt = int(int(json_response['items'][0]['statistics']['videoCount']) / 30) + 1
		driver.get(f'https://www.youtube.com/{split_link[3]}/{user_id}/videos')  # update channel
		title = driver.find_element_by_xpath('//*[@id="text-container"]').text + '.csv'
	elif 'list=' in yt_link:  # Playlists - if its a video in a playlist or the full playlist
		playlist_id = getIDFromLink(yt_link, 'list=')
		driver.get(f'https://www.youtube.com/playlist?list={playlist_id}')
		title = driver.find_element_by_xpath('//*[@id="title"]/yt-formatted-string/a').text + '.csv'
		vids = driver.find_element_by_xpath('//*[@id="stats"]/yt-formatted-string[1]/span[1]').text
		scroll_amnt = math.ceil(int(vids) / 100) + 1
	elif '?' not in yt_link:  # YouTube Homepage
		title_id = 'video-title-link'
		title = 'YouTube Homepage.csv'
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
		print('The entered youtube link is incompatible with the program')
		print('youtube link styles that work:')
		print('\thttps://www.youtube.com/')
		print('\thttps://www.youtube.com/results?search_query=valuetainment')
		print('\thttps://www.youtube.com/watch?v=x9dgZQsjR6s')
		print('\thttps://www.youtube.com/user/patrickbetdavid')
		print('\thttps://www.youtube.com/playlist?list=PLFa0bDwXvBlDGFtce9u__1sBj6fgi21BE')
		driver.close()
		sys.exit(-1)
	# scroll to the bottom of the youtube page
	for i in range(scroll_amnt):
		printProgressBar(i + 1, scroll_amnt, 'Navigating Youtube:', length=50)
		driver.find_element_by_tag_name('body').send_keys(Keys.END)
		sleep(3)

	html = driver.page_source
	soup = BeautifulSoup(html, 'html.parser')
	master_list = []
	if 'list=' not in yt_link and not single_video:  # channel, homepage, and search
		videos = soup.find_all('div', {'id': 'dismissable'})
		for video in videos:
			if 'ytd-shelf-renderer' in video['class'] or 'ytd-compact-promoted-item-renderer' in video['class'] or 'ytd-rich-shelf-renderer' in video['class']:
				continue  # remove the outer most nested 'video'
			data_dict = {}
			# get title
			data_dict['title'] = video.find('a', {'id': title_id}).text.replace('\n', '')
			printProgressBar(videos.index(video) + 1, len(videos), 'Processing Videos:', length=50)
			# get video url + use id for youtube API
			video_id = video.find('a', {'id': title_id})['href'].split('=')[1]
			data_dict, data_dict['comments'] = youtubeAPI(video_id, api_key, data_dict, commentsOn)
			master_list.append(data_dict)
	elif single_video:
		data_dict = {}
		data_dict['title'] = soup.find('meta', {'name': 'title'})['content']
		title = data_dict['title'] + '.csv'
		data_dict, temp_item = youtubeAPI(yt_link.split('=')[1], api_key, data_dict, commentsOn)
		for i in range(1, len(temp_item)):
			for j in range(len(temp_item[0])):
				data_dict[temp_item[0][j]] = temp_item[i][j]
			master_list.append(data_dict)
			data_dict = {}
	else:  # works for playlist
		playlist_videos = soup.find_all('div', {'id': 'contents'})[0]
		videos = playlist_videos.find_all('div', {'id': 'content'})
		for video in videos:
			data_dict = {}
			# get title
			data_dict['title'] = video.find('span', {'id': 'video-title'})['title']
			printProgressBar(videos.index(video) + 1, len(videos), 'Processing Videos:', length=50)
			# get video url + use id for youtube API
			video_id = getIDFromLink(video.find('a', {'class': 'yt-simple-endpoint'})['href'], 'v=')
			data_dict, data_dict['comments'] = youtubeAPI(video_id, api_key, data_dict, commentsOn)
			master_list.append(data_dict)

	print('')  # new line for downloaded file
	driver.close()
	# put data into a CSV file + download to downloads folder
	youtube_df = pd.DataFrame(master_list)
	youtube_df.to_csv(str(Path.home() / "Downloads/") + '/' + title, index=False)
	print('downloaded', title)
