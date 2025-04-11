''' Grab info from terminal. Clean input before trying to run the rest of the script '''
import argparse
import sys
from typing import Optional, Tuple, Dict

VERSION = "1.1"

def supported_styles(link: Optional[str] = None) -> None:
    if link:
        print(f'Error: link style not supported\n\t{link}\n')
    print("\nSupported YouTube Link Styles:")
    print("\thttps://www.youtube.com/")
    print("\thttps://www.youtube.com/results?search_query=valuetainment")
    print("\thttps://www.youtube.com/user/patrickbetdavid")
    print("\thttps://www.youtube.com/channel/UCGX7nGXpz-CmO_Arg-cgJ7A")
    print("\thttps://www.youtube.com/@VALUETAINMENT")
    print("\thttps://www.youtube.com/watch?v=Z2UmjJ2zQkg&list=PLFa0bDwXvBlDGFtce9u__1sBj6fgi21BE")
    print("\thttps://www.youtube.com/watch?v=x9dgZQsjR6s")
    print('\thttps://www.youtube.com/playlist?list=PLFa0bDwXvBlDGFtce9u__1sBj6fgi21BE')

def usage():
    print("Works with: YouTube Homepage, youtube search, channel/user, video, and playlists")
    print(f"\n\nUsage: {sys.argv[0]} [OPTIONS]")
    print("\t--link              \tYouTube link")
    print("\t--api               \tGoogle/YouTube API key")
    print("\t--comments          \tGet comments from YouTube videos")
    print("\t--subtitles         \tGet subtitles from YouTube videos")
    print("\t--playlists         \tGet playlists of a YouTube Channel")
    print("\t--durationseconds   \tGet seconds of video duration")
    print("\t--version           \tList version release")
    print("\t--help              \tShow help menu\n")
    print("Example:")
    print(f"\t{sys.argv[0]} --link [youtube_link] --api [your_api_key] --comments --subtitles --playlists --durationseconds")
    supported_styles()
    sys.exit(1)

def get_commands() -> Tuple[str, str, Dict[str, bool]]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--link", "-l", type=str, help="Specified YouTube link")
    parser.add_argument("--api", "-a", type=str, help="Google YouTube API key")
    parser.add_argument("--comments", "-c", action="store_true", help="Get comments from YouTube videos")
    parser.add_argument("--subtitles", "-s", action="store_true", help="Get subtitles from YouTube videos")
    parser.add_argument("--playlists", "-p", action="store_true", help="Get playlists of a YouTube Channel")
    parser.add_argument("--durationseconds", "-d", action="store_true", help="Get seconds of video duration instead of ISO 8601 duration")
    parser.add_argument("--help", "-h", action="store_true", help="Show help menu")
    parser.add_argument("--version", "-V", action="store_true", help="List version release")

    args = parser.parse_args()

    if args.version:
        print(VERSION)
        sys.exit(0)

    if args.help or not args.api or not args.link or 'www.youtube.com' not in args.link:
        usage()

    options = {
        'cmtOn': args.comments,
        'subOn': args.subtitles,
        'playOn': args.playlists,
        'secOn': args.durationseconds
    }

    return args.link, args.api, options
