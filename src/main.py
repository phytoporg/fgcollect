from searchtweets import load_credentials, gen_request_parameters, collect_results, ResultStream
import argparse
import sys


# Yoinked from example: https://github.com/twitterdev/search-tweets-python/tree/v2
CREDS_YAML_KEY = 'search_tweets_v2'


def log_error(error_string):
    print(f'Error: {error_string}', file=sys.stderr)


def main(args):
    if not args.credentials_file:
        log_error("Missing credentials file!")
        exit(-1)

    if not args.character_tag:
        log_error("No character tag specified!")
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
    query = gen_request_parameters(
        f"#{args.character_tag} has:media",
        results_per_call=results_size,
        granularity=None)
    rs = ResultStream(request_parameters=query, max_results=results_size, max_pages=1, **credentials)
    tweets = list(rs.stream())

    # Original content only, no RTs
    tweet_data = [t['text'] for t in tweets[0]['data'] if not t['text'].startswith('RT')]
    print("\n".join(tweet_data))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--credentials-file', type=str, help="Path to yaml credentials file for API authentication.", required=True)
    parser.add_argument(
        '--character-tag', type=str, help="e.g. MBTL_AO, BBCP_JI, GGXRD_VE", required=True)
    parser.add_argument(
        '--results-size', type=int, help="Number of results to retrieve from Twitter.", default=100)

    main(parser.parse_args())