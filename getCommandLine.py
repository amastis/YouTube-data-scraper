import sys
import getopt

VERSION = "1.0"

def usage():
	print("Usage: " +  sys.argv[0] + " [OPTIONS]")
	print("\t--link		 \tYouTube link")
	print("\t--api	 	\tGoogle/YouTube API key")
	print("\t--comments		Get comments from YouTube videos")
	print("\t\t\t\t   [turning on will increase program run time]")
	print("\t--version       \tList version release")
	print("\t--help          \tThis help menu\n")

	print("Example:")
	print("\t" + sys.argv[0] + " --link [youtube_link] --api [your_api_key] --comments")

	print("\nSupported YouTube Link Styles:")
	print("\thttps://www.youtube.com/")
	print("\thttps://www.youtube.com/results?search_query=valuetainment")
	print("\thttps://www.youtube.com/user/patrickbetdavid")
	print("\thttps://www.youtube.com/channel/UCGX7nGXpz-CmO_Arg-cgJ7A")
	print("\thttps://www.youtube.com/watch?v=Z2UmjJ2zQkg&list=PLFa0bDwXvBlDGFtce9u__1sBj6fgi21BE")
	print("\thttps://www.youtube.com/watch?v=x9dgZQsjR6s")

	print("\nWorks with: YouTube Homepage, youtube search, channel/user, video, and playlists")
	sys.exit(1)

def getCommands():

	youtube_link = None
	api_key = None
	commentsOn = False

	try:
		opts, args = getopt.getopt(sys.argv[1:], "l:a:chv", ["link=", "api=", "comments", "help", "version"])
	except getopt.GetoptError:#, err:
		# print help information and exit:
		print(err) # will print something like "option -a not recognized"
		sys.exit(-1)

	for o, a in opts:
		if o in ("-l", "--link"):
			youtube_link = a
		elif o in ("-a", "--api"):
			api_key = a
		elif o in ("-c", "--comments"):
			commentsOn = True
		elif o in ("-h", "--help"):
			usage()
			sys.exit()
		elif o in ("-V", "--version"):
			print(VERSION)
			sys.exit(0)
		else:
			assert False, "unhandled option"
			sys.exit(-1)

	if youtube_link == None or 'https://www.youtube.com' not in youtube_link or api_key == None:
		usage()

	return youtube_link, api_key, commentsOn