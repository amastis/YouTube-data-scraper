''' generate csv files of user defined youtube links '''
import os
from time import sleep
from pathlib import Path
from math import ceil
from typing import List, Dict, Any

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import trange  # progress bars

# imported local files
from yt_data import Youtube, get_link_id, COMMENT_LABELS
from getCommandLine import get_commands, supported_styles

def get_channel_link(user_id: str, split_link: List[str], new_channel: bool) -> str:
    ''' returns the properly formatted string based on original channel type '''
    if new_channel: # for channels with '@'
        return f'https://www.youtube.com/{user_id}/'
    else:
        return f'https://www.youtube.com/{split_link[3]}/{user_id}/'

def scroll_selenium(driver, scroll_amnt: int, description: str) -> None:
    ''' scrolls to the bottom of the page to load all of the videos in '''
    for _ in trange(scroll_amnt, desc=description):  # scroll to bottom of page
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.END)
        sleep(3)

def load_and_navigate(driver, channel_link: str, page_type: str, load_amnt: int, num_shorts: int) -> None:
    if page_type != 'playlist':
        driver.get(f'{channel_link}{page_type}')
        sleep(5) # replace w/ wait function till elements are visible
    # 48 videos load at a time
    scroll_selenium(driver, abs(num_shorts) // load_amnt + 1, f'Navigating {page_type}') # get all of type

def get_content(driver, scraper, channel_link: str, desc_type: str, load_amnt: int, num_others: int, filter_dict: Dict[str, str]) -> Dict[str, Any]:
    load_and_navigate(driver, channel_link, desc_type, load_amnt, num_others)
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    content = soup.find_all('a', filter_dict, href=True)
    if len(content) == 0:
        content = soup.find_all('a', {'id': 'video-title-link'}, href=True)
    # check if it is a shorts only channel # TODO
    return scraper.video_data(content, desc_type.title())

def main() -> None:
    ''' get user commands and get youtube data to output a csv file in user's download directory '''
    # using getopt to get the commands for the program to run with
    yt_link, api_key, data_opt = get_commands() # data_opt = [cmtOn, subOn, secOn]
    api_key: str = f'&key={api_key}'
    all_links: List[str] = [x for x in yt_link.split(' ') if "youtube" in x]
    scraper: Youtube = Youtube(api_key, data_opt)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument('--blink-settings=imagesEnabled=false')
    os.environ['WDM_LOG_LEVEL'] = "0" # to remove startup logs

    driver = webdriver.Chrome(service=Service(ChromeDriverManager(log_level=0).install()), options=chrome_options)

    for yt_link in all_links: # for multiple links inserted
        print(yt_link, '')
        scroll_amnt: int = 5  # arbitrary number for homepage/search -- get user number to override?
        single_video: bool = False

        title: str = ''
        title_id: str = 'video-title'  # default is for channels
        user_id: str = ''
        channel_link: str = ''
        desc_type: str = '' # switch between channel or playlist
        split_link: List[str] = []
        num_videos: int = 0 # for channels
        videos_flag, shorts_flag, live_flag = False, False, False # for channels
        if any(x in yt_link for x in ['/user/', '/channel/', '/c/', '/@']):  # Channel
            split_link = yt_link.split('/')
            user_id = split_link[-2] if 'videos' in yt_link else split_link[-1]
            user_or_channel: str = f'forUsername={user_id}' if '/user/' in yt_link else 'id='
            if '/user/' not in yt_link:
                driver.get(yt_link)
                sleep(5) # TODO remove this for wait element
                channel: str = driver.find_element(By.XPATH, '/html/body/link[1]').get_attribute('href')
                user_or_channel += get_link_id(channel, '/')
            json_response = scraper.yt_json('channels', 'part=id,statistics', user_or_channel)
            num_videos = int(json_response['items'][0]['statistics']['videoCount'])
            scroll_amnt = num_videos // 30 + 1
            channel_link = get_channel_link(user_id, split_link, '/@' in yt_link)
            driver.get(f'{channel_link}videos')
            if '/@' in yt_link:
                title_id = 'video-title-link'
            sleep(5) # TODO remove this for wait element
            title = driver.find_element(By.XPATH, '//*[@id="text-container"]').text + '.csv'
            # types of videos on the channel
            for item in driver.find_element(By.ID, 'tabsContent').find_elements(By.TAG_NAME, 'tp-yt-paper-tab'):
                if 'VIDEOS' in item.text:
                    videos_flag = True
                    desc_type = 'videos'
                elif 'SHORTS' in item.text:
                    shorts_flag = True
                elif 'LIVE' in item.text:
                    live_flag = True
        elif 'list=' in yt_link:  # Playlists - if its a video in a playlist or the full playlist
            driver.get(f'https://www.youtube.com/playlist?list={get_link_id(yt_link, "list=")}')
            sleep(5) # TODO remove this for wait element
            title = f"{driver.find_elements(By.CLASS_NAME, 'ytd-playlist-header-renderer')[1].find_element(By.ID, 'container').text}.csv"
            vids: int = int(driver.find_element(By.CLASS_NAME, 'byline-item').find_elements(By.TAG_NAME, 'span')[0].text)
            videos_flag = True
            desc_type = 'playlist'
            #title = f"{driver.find_elements(By.TAG_NAME, 'h1')[1].text}.csv"
            #vids: str = driver.find_element(By.ID, 'stats').find_elements(By.TAG_NAME, 'span')[0].text
            scroll_amnt = ceil(int(vids) / 100) + 1
        elif '?' not in yt_link:  # YouTube Homepage
            title, title_id = 'YouTube Homepage.csv', 'video-title-link'
            driver.get(yt_link)
        elif 'v=' in yt_link:  # single YouTube video
            scroll_amnt, single_video = 0, True
            driver.get(yt_link)
        elif 'search_query' in yt_link:  # if using search bar
            driver.get(yt_link)
            title = get_link_id(yt_link, 'search_query=').replace('+', ' ') + '.csv'
        else:  # incompatible link usage
            supported_styles(yt_link)
            continue

        final_list: List[Dict[str, Any]] = []
        if not single_video:  # channel, homepage, and search + playlists
            if videos_flag: # desc_type for videos and playlists
                final_list.extend(get_content(driver, scraper, channel_link, desc_type, 30, num_videos, {'id': title_id})) # TODO change load_amnt 
            if shorts_flag:
                num_others = num_videos - len(final_list) + 1 # 1 for extra row headers
                final_list.extend(get_content(driver, scraper, channel_link, 'shorts', 48, num_others, {'class': 'ytd-rich-grid-slim-media'}))
            if live_flag:
                num_others = num_videos - len(final_list) + 1 # 1 for extra row headers
                final_list.extend(get_content(driver, scraper, channel_link, 'streams', 24, num_others, {'id': title_id}))

        else:  # single video
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            title = soup.find('meta', {'name': 'title'})['content'] + '.csv'
            final_list = scraper.video_data([soup], 'Video')
            # make comments their own items in table
            if data_opt['cmtOn']:
                final_list[0].update(dict(zip(COMMENT_LABELS, final_list[0]['comments'][1])))
                final_list.extend([dict(zip(COMMENT_LABELS, x)) for x in final_list[0]['comments'][2:]])
                del final_list[0]['comments']

        # put data into a CSV file + download to downloads folder
        youtube_df = pd.DataFrame(final_list)
        youtube_df.to_csv(str(Path.home() / "Downloads" / title.replace('/', '')), index=False)
        print(f'\nDownloaded: {title}')
    driver.close()

# BELOW FUNC only for testing 
def test(title: str = 'PLACEHOLDER'):
    #import link_file
    yt_link, api_key, data_opt = get_commands() # data_opt = [cmtOn, subOn, secOn]
    api_key: str = f'&key={api_key}'
    scraper: Youtube = Youtube(api_key, data_opt)
    
    final_list: List[Dict[str, Any]] = []
    final_list = scraper.video_data_from_link(link_file.test, 'Videos')

    # put data into a CSV file + download to downloads folder
    title = f'{title}.csv'
    youtube_df = pd.DataFrame(final_list)
    youtube_df.to_csv(str(Path.home() / "Downloads" / title.replace('/', '')), index=False)
    print(f'\nDownloaded: {title}')

if __name__ == "__main__":
    main()
