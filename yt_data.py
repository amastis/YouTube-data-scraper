''' get and parse all of youtube request/response cycle asked for by user '''
import json
from json import JSONDecodeError
import logging
import re
from typing import Tuple, List, Dict, Any, Union

# other modules
import isodate
import requests
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
from tqdm import tqdm  # progress bars

logging.basicConfig(format='%(levelname)s - %(name)s - %(message)s') #, level=logging.DEBUG)

COMMENT_LABELS = ['comment_id',
                  'comment',
                  'comment_author',
                  'comment_author_url',
                  'comment_likes',
                  'comment_published',
                  'comment_updated_time',
                  'parent_comment']

def _comment_data(item: dict, comment_data: dict, parent: str) -> List[str]:
    # combines all comment meta data into a single list
    return [item['id'],
            comment_data['textOriginal'],
            comment_data['authorDisplayName'],
            comment_data['authorChannelUrl'],
            comment_data['likeCount'],
            comment_data['publishedAt'],
            comment_data['updatedAt'],
            parent]

def get_link_id(yt_link: str, split_by: str = 'v=') -> str:
    ''' returns the link ID from the youtube link given '''
    meta = yt_link.split('?')
    if '&' in meta[-1]:
        meta = [string for string in meta[-1].split('&') if split_by in string]
    elif 'shorts/' in meta[-1]: # for short videos
        meta = meta[-1].split('/')

    return meta[-1].split(split_by)[-1]

def get_caption_str(json_data, language: str) -> str:
    if language not in json_data['automatic_captions']:
        #print('NO CAPTIONS', json_data)
        return ''

    try:
        caption_url: str = [item['url'] for item in json_data['automatic_captions'][language] if item['ext'] == 'json3'][0]
    except IndexError:
        return ''
    if not caption_url:
        #print('NO JSON URL', json_data)
        return ''
    
    response_captions = None
    try:
        response_captions = requests.get(caption_url)
    except:
        print('failed', caption_url) # to diagnose other issues

    if not response_captions:
        return ''

    try:
        automated_captions_dict = response_captions.json()
    except (JSONDecodeError, ValueError) as e:
        print('FAILED', caption_url)
        return ''

    captions_list: List[str] = []
    for item in automated_captions_dict['events']:
        if 'segs' not in item:
            continue
        captions_list.extend([seg['utf8'] for seg in item['segs'] if seg['utf8'] != '\n'])
    
    return ''.join(captions_list)

def get_automated_captions(video_id: str, language: str = 'en') -> str:
    URL: str = f'https://www.youtube.com/watch?v={video_id}'

    # ℹ️ See help(yt_dlp.YoutubeDL) for a list of available options and public functions
    ydl_opts: Dict[str, Union[str, List[str], bool]] = {
        'subtitleslangs': [language],
        'skip_download': True,
        'subtitlesformat': 'json3',
        'writeautomaticsub': True,
        'outtmpl': '/tmp/sub.json',
        # https://github.com/yt-dlp/yt-dlp/issues/10128
        'sleep-interval': 60, # ADDED sleep intervals 
        'min-sleep-interval': 60,
        'max-sleep-interval': 90,
    }
    link_to_download: str = ''

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(URL, download=False)
        except Exception as e: # yt_dlp.utils.DownloadError
            print(e)
            return ''

        # ℹ️ ydl.sanitize_info makes the info json-serializable
        link_to_download = ydl.sanitize_info(info)
        #print(link_to_download)
    
    return get_caption_str(link_to_download, language)

def get_captions(vid_id: str) -> str:
    ''' gets the subtitles / captions from the video that's already generated '''
    try:
        captions: List[Dict[str, str]] = YouTubeTranscriptApi.get_transcript(vid_id)
    except Exception:  # no transcript for video
        captions = []

    if not captions:
        return '', get_automated_captions(vid_id)

    return [str(item['start'] - item['duration']) for item in captions], [item['text'] for item in captions]
    #return " ".join([item['text'] for item in captions])

class Youtube():
    ''' Interact with the YouTube API to retrive info about the list of videos (by ID) given '''
    def __init__(self, api_key: str, data_options: Dict[str, bool]):
        self.api_key: str = api_key
        self.data_opt: Dict[str, bool] = data_options
        self.session = requests.Session()

    def yt_json(self, directory: str, parts: str, item_id: str, new_page_token: str = '') -> dict:
        ''' format url to send requests and retrieve response
        parts and item_id will have to be properly formmated '''
        url: str = f'https://www.googleapis.com/youtube/v3/{directory}?{parts}&{item_id}{self.api_key}'
        if new_page_token:
            url += f'&pageToken={new_page_token}'
        if directory not in ['videos', 'channels']:
            url += '&maxResults=100'
        try:
            json_response = self.session.get(url).json()
        except Exception:
            return self.yt_json(directory, parts, item_id, new_page_token)
        return json_response

    # get commentThreads and comment replies from the video
    def _get_comments(self, d_type: str, vid_type: str, parts: str = 'part=snippet', parent: str = 'id') -> Tuple[list, list]:
        ''' get commentThreads and comment replies from the video '''
        is_thread, next_pg = d_type == 'Thread', ''
        if is_thread:
            parts, parent = f'{parts},replies', 'id'
        all_comments, comments_with_replies, json_data = [], [], []
        while True:  # or 'nextPageToken' in json_comments:
            json_comments = self.yt_json(f'comment{d_type}s', parts, vid_type, next_pg)
            if 'items' in json_comments:
                json_data += json_comments['items']
            else:
                print(json_comments) # prints errors -> TRY to handle better
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
                        all_comments.append(_comment_data(n_item, n_item['snippet'], item[parent]))
                    #all_cmnts = [cmntData(elm, elm['snippet'], item[parent]) for elm in item['replies']['comments']]
                elif 'replies' in item:
                    comments_with_replies.append(item['id'])
            all_comments.append(_comment_data(item, cData, item[parent]))
        return all_comments, comments_with_replies

    def _youtube_api(self, video_id: str, data_dict: Dict[str, Any]) -> Tuple[Dict[str, Any], list]:
        '''  query youtube API to get data from the video_id specified. '''
        json_parts: str = 'part=snippet,statistics,contentDetails,topicDetails'
        json_response = self.yt_json('videos', json_parts, f'&id={video_id}')
        allComments = None#[]

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
                    allComments = []
                    allComments.append(COMMENT_LABELS)
                    temp_data, c_replies = self._get_comments('Thread', f'videoId={video_id}')
                    allComments += temp_data
                    # comments that have more replies than can obtain via thread replies
                    for comment_id in c_replies:
                        temp_data, _ = self._get_comments('', f'parentId={comment_id}')
                        allComments += temp_data
                    #a, b = zip(*[self._getComments('', f'parentId={x}') for x in c_replies])
                    #allComments.extend([item for sublist in list(a) for item in sublist]) # flatten list

            else:
                data_dict['comment_number'] = 0
            snippet = json_response['items'][0]['snippet']
            data_dict['title'] = snippet['title']
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

    def video_data(self, videos: list, desc_type: str) -> List[Dict[str, Any]]:
        ''' main function to get all of the data from the list of videos given '''
        final_list: List[Dict[str, Any]] = []
        for video in tqdm(videos, desc=f'Processing {desc_type}'):
            data_dict: Dict[str, Any] = {}
            if 'id' in video.attrs and 'title' not in video.attrs: # element is a valid element, but doesn't have info in it # TODO CHECK for single video that has aria-label
                continue

            try:  # get video url + use id for youtube API
                vid_id = get_link_id(video['href'])
            except Exception: # for single videos exception handling
                '''
                pattern = re.compile(r'{"videoId":".{1,20}"}', re.MULTILINE | re.DOTALL)
                script = video.find('script', text=pattern)
                vid_id = json.loads(re.search(pattern, script.string)[0])['videoId']
                '''
                video_url = video.find('meta', property='og:url', content=True)['content'] # IF NoneType here --> video no longer exists either (deleted, private)
                vid_id = get_link_id(video_url)

            if self.data_opt['subOn']:
                data_dict['captions'] = get_captions(vid_id)
            data_dict['video_url'] = f'https://www.youtube.com/watch?v={vid_id}'
            try:
                data_dict, data_dict['comments'] = self._youtube_api(vid_id, data_dict)
                if not data_dict['comments']: # remove comments column if no comments
                    del data_dict['comments']
            except ValueError:  # for exceeding api quota
                final_list.append(data_dict)
                logging.info('\nquota reached')
                break
            final_list.append(data_dict)
        return final_list

    # BELOW FUNC for testing currently + using in case selenium unable to load vids on channel and self get links
    def video_data_from_link(self, videos: list, desc_type: str) -> List[Dict[str, Any]]:
        ''' main function to get all of the data from the list of videos given '''
        final_list: List[Dict[str, Any]] = []
        for video in tqdm(videos, desc=f'Processing {desc_type}'):
            data_dict: Dict[str, Any] = {}
            vid_id = get_link_id(video)

            if self.data_opt['subOn']:
                data_dict['captions'] = get_captions(vid_id)
            data_dict['video_url'] = f'https://www.youtube.com/watch?v={vid_id}'
            try:
                data_dict, data_dict['comments'] = self._youtube_api(vid_id, data_dict)
                if not data_dict['comments']: # remove comments column if no comments
                    del data_dict['comments']
            except ValueError:  # for exceeding api quota
                final_list.append(data_dict)
                logging.info('\nquota reached')
                break
            final_list.append(data_dict)
        return final_list
