from searchtweets import load_credentials, gen_request_parameters, collect_results, ResultStream
import argparse
import json
import os
import sys
import yt_dlp

# Yoinked from example: https://github.com/twitterdev/search-tweets-python/tree/v2
CREDS_YAML_KEY = 'search_tweets_v2'


def log_error(error_string):
    print(f'Error: {error_string}', file=sys.stderr)


def check_filepath_arg(arg_friendly_name, arg_value, create_dir_if_missing=True):
    if not arg_value:
        log_error(f'Missing {arg_friendly_name} path argument.')
        return False

    if not os.path.exists(arg_value):
        log_error(f'Path {arg_value} does not exist.')

        if create_dir_if_missing:
            log_error(f'Creating {arg_friendly_name} directory {arg_value}... ')
            os.makedirs(arg_value)
            log_error(f'Successfully created {arg_value}')
        else:
            return False

    return True


def main(args):
    if not check_filepath_arg('credentials file', args.credentials_file, create_dir_if_missing=False):
        exit(-1)

    if not args.character_tag:
        log_error("No character tag specified!")
        exit(-1)

    if not check_filepath_arg('downloads path', args.downloads_path):
        exit(-1)

    try:
        credentials = load_credentials(filename=args.credentials_file, yaml_key=CREDS_YAML_KEY, env_overwrite=False)
    except KeyError:
        log_error(f'Could not find provided yaml key in credentials file {args.credentials_file}')
        exit(-1)

    assert args.results_size is not None, "--results-size should have a default value."
    results_size = args.results_size

    # Specifying a granularity causes the returned results to contain only the tweet counts for durations specified
    # by that granularity (i.e. minutes, hours, days). Not useful here, but the positional argument is required, so
    # just make it None.

    # We're looking for original, video-based content only.
    results_per_call = min(100, args.results_size)
    query = gen_request_parameters(
        f"#{args.character_tag} has:videos -is:retweet",
        results_per_call=results_per_call,
        granularity=None)
    rs = ResultStream(request_parameters=query, max_tweets=args.results_size, max_requests=1, **credentials)
    tweets = list(rs.stream())
    if len(tweets) == 0:
        print(f'No tweets found for tag: #{args.character_tag}')
        exit(0)

    tweet_data = [t for t in tweets[0]['data']]
    print(f'Retrieved {len(tweet_data)} results. Fetching content to {args.downloads_path}.')

    video_urls = []
    for tweet in tweet_data:
        tweet_id = tweet['id']
        target_download_prefix = os.path.join(args.downloads_path, tweet_id)
        if os.path.exists(target_download_prefix + ".mp4") and os.path.exists(target_download_prefix + ".json"):
            # Skip this one if we already have it
            print(f'Already have data for tweet ID {tweet_id} in target download path {args.downloads_path}. Skipping.')
            continue

        # Takes an enterprise API account to do this properly. Video attachment links so far appear to show up
        # as the last token in all of the tweets I've seen. Hopefully that pattern always holds, and if not, we'll
        # cross that bridge later.
        video_url = tweet['text'].split()[-1]
        video_urls.append(video_url)

    # Do some stuff as each video is downloaded.
    def report_ytdl_progress(params):
        status = params['status']
        if status == 'finished':
            # Only write the tweet content file if the download succeeded.
            info_dict = params['info_dict'].copy()
            tweet_id = info_dict['id']

            tweet_text_filename = os.path.join(args.downloads_path, f'{tweet_id}.json')
            with open(tweet_text_filename, 'w') as fw:
                # Just write the useful stuff
                info_dict.pop('formats')
                info_dict.pop('thumbnails')
                info_dict.pop('http_headers')

                # For clarity
                info_dict['tweet_text'] = info_dict['title']
                info_dict.pop('title')

                # Make it pretty for us humies
                fw.write(json.dumps(info_dict, indent=4))

            print(f'{params["filename"]} download completed! Wrote metadata to {tweet_text_filename}')
        elif status == 'error':
            log_error(f'Failed to download {params["filename"]}')

    yt_dlp_opts = {
        'final_ext': '                   mp4',
        'outtmpl':                       os.path.join(args.downloads_path, '%(id)s.%(ext)s'),
        'progress_hooks':                {report_ytdl_progress},
        'quiet':                         True,
        'noprogress':                    True,
        'concurrent_fragment_downloads': True,
    }
    with yt_dlp.YoutubeDL(yt_dlp_opts) as ytdl:
        ytdl.download(video_urls)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--credentials-file', type=str, help="Path to yaml credentials file for API authentication.", required=True)
    parser.add_argument(
        '--character-tag', type=str, help="e.g. MBTL_AO, BBCP_JI, GGXRD_VE", required=True)
    parser.add_argument(
        '--downloads-path', type=str, help="Path to place video and tweet results.", required=True)
    parser.add_argument(
        '--results-size', type=int, help="Number of results to retrieve from Twitter.", default=10)

    main(parser.parse_args())
