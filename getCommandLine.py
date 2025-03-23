''' Grab info from terminal. Clean input before trying to run the rest of the script '''
import sys
import getopt  # change to argparse
from typing import Optional, Tuple, Dict, List

VERSION = "1.1"

def supported_styles(link: Optional[str] = None) -> None:
    ''' shows supported url styles in terminal '''
    if link:
        print(f'Error: link style not supported\n\t{link}\n')
    print("\nSupported YouTube Link Styles:")
    print("\thttps://www.youtube.com/")
    print("\thttps://www.youtube.com/results?search_query=valuetainment")
    print("\thttps://www.youtube.com/user/patrickbetdavid")
    print("\thttps://www.youtube.com/channel/UCGX7nGXpz-CmO_Arg-cgJ7A")
    print("\thttps://www.youtube.com/watch?v=Z2UmjJ2zQkg&list=PLFa0bDwXvBlDGFtce9u__1sBj6fgi21BE")
    print("\thttps://www.youtube.com/watch?v=x9dgZQsjR6s")
    print('\thttps://www.youtube.com/playlist?list=PLFa0bDwXvBlDGFtce9u__1sBj6fgi21BE')

def usage() -> None:
    ''' show usage information in terminal '''
    print("Works with: YouTube Homepage, youtube search, channel/user, video, and playlists")
    print(f"\n\nUsage: {sys.argv[0]} [OPTIONS]")
    print("\t--link		 \tYouTube link")
    print("\t--api	 	\tGoogle/YouTube API key")
    print("\t--comments		Get comments from YouTube videos")
    print("\t\t\t\t   [turning on will increase program run time]")
    print("\t--subtitles		Get subtitles from YouTube videos")
    print("\t--playlists        Get playlists of a YouTube Channel and show the playlist(s) a  video belongs to")
    print("\t--durationseconds	Get seconds of YouTube video duration (instead of ISO 8601 duration)")
    print("\t--version       \tList version release")
    print("\t--help          \tThis help menu\n")

    print("Example:")
    print(f"\t{sys.argv[0]} --link [youtube_link] --api [your_api_key] --comments --subtitles --playlists --durationseconds")
    supported_styles()
    sys.exit(1)

def get_commands() -> Tuple[str, str, Dict[str, bool]]:
    ''' get arguments from command line and parse them '''

    youtube_link: str = ''
    api_key: str = ''
    comments_on: bool = False
    subtitiles_on: bool = False
    seconds_on: bool = False
    playlists_on: bool = False
    args_values: List[str] = ["link=", "api=", "comments", "subtitles", "playlists", "durationseconds", "help", "version"]

    try:
        opts, _ = getopt.getopt(sys.argv[1:], "l:a:cspdhv", args_values)
    except getopt.GetoptError as err: # print help information and exit:
        print(err) # will print something like "option -a not recognized"
        sys.exit(-1)

    for option, value in opts:
        if option in ("-l", "--link"):
            youtube_link = value
        elif option in ("-a", "--api"):
            api_key = value
        elif option in ("-c", "--comments"):
            comments_on = True
        elif option in ("-s", "--subtitles"):
            subtitiles_on = True
        elif option in ("-p", "--playlists"):
            playlists_on = True
        elif option in ("-d", "--durationseconds"):
            seconds_on = True
        elif option in ("-h", "--help"):
            usage()
            sys.exit()
        elif option in ("-V", "--version"):
            print(VERSION)
            sys.exit(0)
        else:
            assert False, "unhandled option"
            sys.exit(-1)

    if not api_key or not youtube_link or 'www.youtube.com' not in youtube_link:
        usage()
    options = {'cmtOn': comments_on, 'subOn': subtitiles_on, 'playOn': playlists_on, 'secOn': seconds_on}

    return youtube_link, api_key, options
