import requests
import isodate
import json
import logging
import re
from typing import Tuple
from youtube_transcript_api import YouTubeTranscriptApi
from tqdm import tqdm  # progress bars
from bs4 import BeautifulSoup

logging.basicConfig(format='%(levelname)s - %(name)s - %(message)s') #, level=logging.DEBUG)

COMMENT_LABELS = ['comment_id', 'comment', 'comment_author', 'comment_author_url', 'comment_likes', 'comment_published', 'comment_updated_time', 'parent_comment']

# combines all comment meta data into a single array
def _commentData(item: dict, cData: dict, parent: str) -> list:
    return [item['id'], cData['textOriginal'], cData['authorDisplayName'], cData['authorChannelUrl'], cData['likeCount'], cData['publishedAt'], cData['updatedAt'], parent]

def getLinkID(yt_link: str, split_by: str = 'v=') -> str:
    meta = yt_link.split('?')
    if '&' in meta[-1]:
        meta = [string for string in meta[-1].split('&') if split_by in string]
    return meta[-1].split(split_by)[-1]

# gets the subtitles / captions from the video that's already generated
def getCaptions(vid_id: str) -> str:
    try:
        captions = YouTubeTranscriptApi.get_transcript(vid_id)
    except:  # no transcript for video
        return ""
    return " ".join([item['text'] for item in captions])


class Youtube():
    def __init__(self, api_key, data_options):
        self.api_key = api_key
        self.data_opt = data_options

    # parts and item_id will have to be properly formmated
    def _YT_json(self, directory: str, parts: str, item_id: str, new_Page_Token: str = '') -> dict:
        url = f'https://www.googleapis.com/youtube/v3/{directory}?{parts}&{item_id}{self.api_key}'
        if new_Page_Token:
            url += f'&pageToken={new_Page_Token}'
        if directory != 'videos' and directory != 'channels':
            url += '&maxResults=100'
        try:
            print(type(requests.get(url).json()))
            json_response = requests.get(url).json()
        except:
            return self._YT_json(directory, parts, item_id, new_Page_Token)
        return json_response

    # get commentThreads and comment replies from the video 
    def _getComments(self, d_type: str, vid_type: str, parts: str = 'part=snippet', parent: str = 'id') -> Tuple[list, list]:
        is_thread, next_pg = d_type == 'Thread', ''
        if is_thread:
            parts, parent = f'{parts},replies', 'id'
        all_comments, comments_with_replies, json_data = [], [], []
        while True:  # or 'nextPageToken' in json_comments:
            json_comments = self._YT_json(f'comment{d_type}s', parts, vid_type, next_pg)
            if 'items' in json_comments:
                json_data += json_comments['items']
            else: 
                print(json_comments)  # prints errors -> TRY to handle better
            if 'nextPageToken' not in json_comments:  # exit loop condition
                break
            next_pg = json_comments['nextPageToken']
        for item in json_data:
            cData = item['snippet']  # comments
            if is_thread: 
                cData = item['snippet']['topLevelComment']['snippet']  # commentThreads
                reply_num = int(item['snippet']['totalReplyCount'])
                if reply_num < 6 and 'replies' in item:  # add comments (available w/ response)
                    for n_item in item['replies']['comments']:
                        all_comments.append(_commentData(n_item, n_item['snippet'], item[parent]))
                    #all_cmnts = [cmntData(elm, elm['snippet'], item[parent]) for elm in item['replies']['comments']]
                elif 'replies' in item:
                    comments_with_replies.append(item['id']) 
            all_comments.append(_commentData(item, cData, item[parent]))
        return all_comments, comments_with_replies

    # youtube API to get more specific information about the video
    def _youtubeAPI(self, video_id: str, data_dict: dict) -> Tuple[dict, list]:
        json_parts = 'part=snippet,statistics,contentDetails,topicDetails'
        json_response = self._YT_json('videos', json_parts, f'&id={video_id}')
        allComments = []
        
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
                if self.data_opt['cmtOn']:  # cycle through the various comments on the video
                    allComments.append(COMMENT_LABELS)
                    temp_data, c_replies = self._getComments('Thread', f'videoId={video_id}')
                    allComments += temp_data
                    # comments that have more replies than can obtain via thread replies
                    for comment_id in c_replies:
                        temp_data, _ = self._getComments('', f'parentId={comment_id}')
                        allComments += temp_data
                    #a, b = zip(*[self._getComments('', f'parentId={x}') for x in c_replies])
                    #allComments.extend([item for sublist in list(a) for item in sublist]) # flatten list

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
            if self.data_opt['secOn']:
                data_dict['seconds_duration'] = isodate.parse_duration(video_duration).total_seconds()
            else:
                data_dict['ISO_8601_duration'] = video_duration
            if 'topicDetails' in json_response['items'][0]:
                data_dict['video_topics'] = json_response['items'][0]['topicDetails']['topicCategories']

        return data_dict, allComments

    # main function to get all of the data from the videos 
    def videoData(self, videos: list) -> list:
        final_list = []
        for video in tqdm(videos, desc='Processing Videos'):
            data_dict = {}
            try:  # get title
                data_dict['title'] = video['title']
            except TypeError:
                logging.debug("Getting data for a single video.")

            try:  # get video url + use id for youtube API
                vid_id = getLinkID(video['href'])
            except:
                pattern = re.compile(r'{"videoId":".{1,20}"}', re.MULTILINE | re.DOTALL)
                script = video.find('script', text=pattern)
                vid_id = json.loads(re.search(pattern, script.string).group(0))['videoId']
            if self.data_opt['subOn']:
                data_dict['captions'] = getCaptions(vid_id)
            data_dict['video_url'] = f'https://www.youtube.com/watch?v={vid_id}'
            try:
                data_dict, data_dict['comments'] = self._youtubeAPI(vid_id, data_dict)
            except ValueError:  # for exceeding api quota
                final_list.append(data_dict)
                logging.info('\nquota reached')
                break
            final_list.append(data_dict)
        return final_list
