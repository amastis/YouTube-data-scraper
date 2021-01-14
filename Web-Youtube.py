from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from getCommandLine import getCommands
from bs4 import BeautifulSoup
from time import sleep
import pandas as pd
import requests
import json 
import math
import sys
import re

# youtube API to get more specific information about the video
def youtubeAPI(video_id, api_key, data_dict, commentsOn):
	json_response = requests.get('https://www.googleapis.com/youtube/v3/videos?part=snippet&part=statistics&part=contentDetails&part=topicDetails&id=' + video_id + '&key=' + api_key).json()
	allComments = []

	if json_response['pageInfo']['totalResults'] != 0: # to deal with deleted and private videos in playlists (mainly)
		statistics = json_response['items'][0]['statistics']
		data_dict['views'] = statistics['viewCount']
		data_dict['likes'] = statistics['likeCount'] if 'likeCount' in statistics else 0
		data_dict['dislikes'] = statistics['dislikeCount'] if 'dislikeCount' in statistics else 0
		data_dict['favorites'] = statistics['favoriteCount']
		if 'commentCount' in statistics and int(statistics['commentCount']) > 0:
			data_dict['comment_number'] = statistics['commentCount']
			if commentsOn: # to cycle through the various comments on the video
				json_comment_response = requests.get('https://www.googleapis.com/youtube/v3/commentThreads?videoId=' + video_id + '&part=id&part=snippet&part=replies&maxResults=100&key=' + api_key).json()
				page_Total_Results = int(json_comment_response['pageInfo']['totalResults'])
				next_Page_Token = json_comment_response['nextPageToken'] if 'nextPageToken' in json_comment_response else 'true'
				
				commentSetup = ['comment_id', 'comment', 'comment_author', 'comment_author_url', 'comment_likes', 'comment_published', 'comment_updated_time', 'parent_comment']
				allComments.append(commentSetup)
				comments_with_replies = []
				while next_Page_Token != None:
					for i in range(page_Total_Results):
						commentData = json_comment_response['items'][i]['snippet']['topLevelComment']['snippet']
						comment = [json_comment_response['items'][i]['id'], commentData['textOriginal'], commentData['authorDisplayName'], commentData['authorChannelUrl'], commentData['likeCount'], commentData['publishedAt'], commentData['updatedAt'], json_comment_response['items'][i]['snippet']['topLevelComment']['id']]
						allComments.append(comment) 
						if int(json_comment_response['items'][i]['snippet']['totalReplyCount']) > 0:
							comments_with_replies.append(json_comment_response['items'][i]['id'])
					if 'nextPageToken' not in json_comment_response:
						next_Page_Token = None
					else: 
						next_Page_Token = json_comment_response['nextPageToken']
						json_comment_response = requests.get('https://www.googleapis.com/youtube/v3/commentThreads?videoId=' + video_id + '&pageToken=' + next_Page_Token + '&part=snippet&part=replies&maxResults=100&key=' + api_key).json() 
						page_Total_Results = int(json_comment_response['pageInfo']['totalResults'])
				for comment_id in comments_with_replies:
					json_comment_response = requests.get('https://www.googleapis.com/youtube/v3/comments?part=snippet&parentId=' + comment_id + '&maxResults=100&key=' + api_key).json()
					page_Total_Results = len(json_comment_response['items'])
					for i in range(page_Total_Results):
						commentData = json_comment_response['items'][i]['snippet']
						comment = [json_comment_response['items'][i]['id'], commentData['textOriginal'], commentData['authorDisplayName'], commentData['authorChannelUrl'], commentData['likeCount'], commentData['publishedAt'], commentData['updatedAt'], commentData['parentId']]
						allComments.append(comment) 
						if i == page_Total_Results - 1 and 'nextPageToken' in json_comment_response:
							next_Page_Token = json_comment_response['nextPageToken']
							json_comment_response = requests.get('https://www.googleapis.com/youtube/v3/comments?part=snippet&parentId=' + comment_id + '&pageToken=' + next_Page_Token + '&maxResults=100&key=' + api_key).json()
							i = 0
							page_Total_Results = len(json_comment_response['items'])
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

def getIDFromLink(youtube_link, splitThis):
	meta = youtube_link.split('?')
	if '&' in meta[-1]:
		meta = [string for string in meta[-1].split('&') if splitThis in string]
	youtube_id = meta[-1].split(splitThis)[-1]
	return youtube_id

if __name__ == "__main__":

	# using getopt to get the commands for the program to run with
	youtube_link, api_key, commentsOn = getCommands()

	csv_title = ''
	scroll_amount = 50 # arbitrary number for homepage and search -- could have the user insert a number to override?
	single_video = False
	chrome_options = Options()
	chrome_options.add_argument("--headless")
	driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

	title_id = 'video-title' # default is for channels
	if '/user/' in youtube_link or '/channel/' in youtube_link or '/c/' in youtube_link: # Channel
		split_link = youtube_link.split('/')
		user_id = split_link[-2] if 'videos' in youtube_link else split_link[-1]
		user_or_channel = '&forUsername=' + user_id if '/user/' in youtube_link else '&id=' + user_id # &forUsername=
		json_response = requests.get('https://www.googleapis.com/youtube/v3/channels?part=id&part=statistics' + user_or_channel + '&key=' + api_key).json() # to get number of videos on the channel
		scroll_amount = math.ceil((int(json_response['items'][0]['statistics']['videoCount']) - 60) / 30) + 2
		driver.get('https://www.youtube.com/' + split_link[3] + '/' + user_id + '/videos') # update channel to get
		csv_title = driver.find_element_by_xpath('/html/body/ytd-app/div/ytd-page-manager/ytd-browse/div[3]/ytd-c4-tabbed-header-renderer/app-header-layout/div/app-header/div[2]/div[2]/div/div[1]/div/div[1]/ytd-channel-name/div/div/yt-formatted-string').text + '.csv'
	elif 'list=' in youtube_link: # Playlists - works for both if its a video in a playlist and if it is the full playlist
		playlist_id = getIDFromLink(youtube_link, 'list=')
		driver.get('https://www.youtube.com/playlist?list=' + playlist_id)
		csv_title = driver.find_element_by_xpath('//*[@id="title"]/yt-formatted-string/a').text + '.csv'
		video_count = driver.find_element_by_xpath('//*[@id="stats"]/yt-formatted-string[1]/span[1]').text
		scroll_amount = math.ceil(int(video_count) / 100) + 1
	elif '?' not in youtube_link: # YouTube Homepage
		title_id = 'video-title-link'
		csv_title = 'YouTube Homepage.csv'
		driver.get(youtube_link)
	elif 'v=' in youtube_link: # single YouTube video
		scroll_amount = 0
		single_video = True
		driver.get(youtube_link)
	elif 'search_query' in youtube_link: # if using search bar
		driver.get(youtube_link)
		meta = youtube_link.split('search_query=')[1]
		if '&' in meta: # for extra commands tacked on
			meta = meta.split('&')[0]
		csv_title = meta.replace('+', ' ') + '.csv'
	else: # improper usage
		print('The entered youtube link is incompatible with the program')
		print('youtube link styles that work:\nhttps://www.youtube.com/\nhttps://www.youtube.com/results?search_query=valuetainment\nhttps://www.youtube.com/watch?v=x9dgZQsjR6s\nhttps://www.youtube.com/user/patrickbetdavid\nhttps://www.youtube.com/playlist?list=PLFa0bDwXvBlDGFtce9u__1sBj6fgi21BE')
		driver.close()
		sys.exit(-1)
	
	for _ in range(scroll_amount): # scroll to the bottom of the youtube page
		driver.find_element_by_tag_name('body').send_keys(Keys.END)
		sleep(3)

	html = driver.page_source
	soup = BeautifulSoup(html, 'html.parser')

	master_list = []
	if 'list=' not in youtube_link and not single_video: # channel, homepage, and search
		videos = soup.find_all('div', {'id': 'dismissable'})
		for video in videos:
			if 'ytd-shelf-renderer' in video['class'] or 'ytd-compact-promoted-item-renderer' in video['class'] or 'ytd-rich-shelf-renderer' in video['class']: 
				continue # remove the outer most nested 'video'
			data_dict = {}
			# get title
			data_dict['title'] = video.find('a', {'id': title_id}).text.replace('\n', '')
			print(data_dict['title']) # just to see the 'progress' of the script
			# get video url + use id for youtube API
			video_id = video.find('a', {'id': title_id})['href'].split('=')[1]
			data_dict['video_url'] = 'https://www.youtube.com/watch?v=' + video_id
			
			data_dict, data_dict['comments'] = youtubeAPI(video_id, api_key, data_dict, commentsOn)
			master_list.append(data_dict)
	elif single_video: 
		data_dict = {}
		data_dict['title'] = soup.find('meta', {'name': 'title'})['content']
		csv_title = data_dict['title'] + '.csv'
		data_dict['video_url'] = youtube_link
		data_dict, temp_item = youtubeAPI(youtube_link.split('=')[1], api_key, data_dict, commentsOn)
		for i in range(1, len(temp_item)):
			for j in range(len(temp_item[0])):
				data_dict[temp_item[0][j]] = temp_item[i][j]
			master_list.append(data_dict)
			data_dict = {}
	else: # works for playlist
		playlist_videos = soup.find_all('div', {'id': 'contents'})[0]
		videos = playlist_videos.find_all('div', {'id': 'content'})
		for video in videos:
			data_dict = {}
			# get title
			data_dict['title'] = video.find('span', {'id': 'video-title'})['title']
			print(data_dict['title']) # just to see the 'progress' of the script
			# get video url + use id for youtube API
			video_id = getIDFromLink(video.find('a', {'class': 'yt-simple-endpoint'})['href'], 'v=')
			data_dict['video_url'] = 'https://www.youtube.com/watch?v=' + video_id
			
			data_dict, data_dict['comments'] = youtubeAPI(video_id, api_key, data_dict, commentsOn)
			master_list.append(data_dict)

	driver.close()
	# put data into a CSV file
	youtube_df = pd.DataFrame(master_list)
	youtube_df.to_csv(csv_title, index=False)
	print('downloaded', csv_title)

