from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from time import sleep
from pathlib import Path
import pandas as pd
from math import ceil
from tqdm import trange  # progress bars
# imported files
from yt_data import Youtube, getLinkID
from getCommandLine import getCommands, supportedStyles


def main() -> None:
	# using getopt to get the commands for the program to run with
	yt_link, api_key, data_opt = getCommands() # data_opt = [cmtOn, subOn, secOn]
	api_key = '&key=' + api_key
	all_links = [x for x in yt_link.split(' ') if "youtube" in x]
	scraper = Youtube(api_key, data_opt)
	chrome_options = Options()
	chrome_options.add_argument("--headless")
	driver = webdriver.Chrome(ChromeDriverManager().install(), options=chrome_options)

	for yt_link in all_links: # for multiple links inserted
		print(yt_link, '')
		scroll_amnt = 5  # arbitrary number for homepage/search -- user insert number to override?
		single_video = False

		title, title_id = '', 'video-title'  # default is for channels
		if any(x in yt_link for x in ['/user/', '/channel/', '/c/']):  # Channel
			split_link = yt_link.split('/')
			user_id = split_link[-2] if 'videos' in yt_link else split_link[-1]
			user_or_channel = f'&forUsername={user_id}' if '/user/' in yt_link else '&id='
			if '/user/' not in yt_link:
				driver.get(yt_link)
				channel = driver.find_element_by_xpath('/html/body/link[1]').get_attribute('href')
				user_or_channel += getLinkID(channel, '/')
			json_response = scraper._YT_json('channels', 'part=id,statistics', user_or_channel)
			scroll_amnt = int(int(json_response['items'][0]['statistics']['videoCount']) / 30) + 1
			driver.get(f'https://www.youtube.com/{split_link[3]}/{user_id}/videos')  # update channel
			title = driver.find_element_by_xpath('//*[@id="text-container"]').text + '.csv'
		elif 'list=' in yt_link:  # Playlists - if its a video in a playlist or the full playlist
			driver.get(f'https://www.youtube.com/playlist?list={getLinkID(yt_link, "list=")}')
			title = driver.find_elements_by_tag_name('h1')[1].text + '.csv'
			vids = driver.find_element_by_id('stats').find_elements_by_tag_name('span')[0].text
			scroll_amnt = ceil(int(vids) / 100) + 1
		elif '?' not in yt_link:  # YouTube Homepage
			title, title_id = 'YouTube Homepage.csv', 'video-title-link'
			driver.get(yt_link)
		elif 'v=' in yt_link:  # single YouTube video
			scroll_amnt, single_video = 0, True
			driver.get(yt_link)
		elif 'search_query' in yt_link:  # if using search bar
			driver.get(yt_link)
			title = getLinkID(yt_link, 'search_query=').replace('+', ' ') + '.csv'
		else:  # incompatible link usage
			supportedStyles(yt_link)
			continue
		
		for _ in trange(scroll_amnt, desc='Navigating Youtube'):  # scroll to bottom of page
			driver.find_element_by_tag_name('body').send_keys(Keys.END)
			sleep(3)

		soup = BeautifulSoup(driver.page_source, 'html.parser')
		final_list = []
		if not single_video:  # channel, homepage, and search + playlists
			videos = soup.find_all('a', {'id': title_id})
			final_list = scraper.videoData(videos)
		else:  # single video
			title = soup.find('meta', {'name': 'title'})['content'] + '.csv'
			final_list = scraper.videoData([soup])
			# make comments their own items in table
			final_list[0].update(dict(zip(COMMENT_LABELS, final_list[0]['comments'][1])))
			final_list.extend([dict(zip(COMMENT_LABELS, x)) for x in final_list[0]['comments'][2:]])
			del final_list[0]['comments']

		# put data into a CSV file + download to downloads folder
		youtube_df = pd.DataFrame(final_list)
		youtube_df.to_csv(str(Path.home() / "Downloads/") + '/' + title, index=False)
		print(f'\nDownloaded: {title}')
	driver.close()


if __name__ == "__main__":
	main()
