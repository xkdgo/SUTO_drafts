import aiohttp
import asyncio
import async_timeout
from random import randint
import logging
from datetime import datetime
import argparse
from bs4 import BeautifulSoup


LOGGER_FORMAT = '%(asctime)s %(message)s'
TOP_STORIES_URL = "http://news.ycombinator.com"
FETCH_TIMEOUT = 10
MAXIMUM_FETCHES = 5

parser = argparse.ArgumentParser(
    description='Calculate the number of comments of the top stories in HN.')
parser.add_argument(
    '--period', type=int, default=5, help='Number of seconds between poll')
parser.add_argument(
    '--limit', type=int, default=5,
    help='Number of new stories to calculate comments for')
parser.add_argument('--verbose', action='store_true', help='Detailed output')


logging.basicConfig(format=LOGGER_FORMAT, datefmt='[%H:%M:%S]')
log = logging.getLogger()
log.setLevel(logging.INFO)


class BoomException(Exception):
    pass


class URLFetcher():
    """Provides counting of URL fetches for a particular task.
    """

    def __init__(self):
        self.fetch_counter = 0

    async def fetch(self, session, url):
        """Fetch a URL using aiohttp returning parsed response text.
        As suggested by the aiohttp docs we reuse the session.
        """
        with async_timeout.timeout(FETCH_TIMEOUT):
            self.fetch_counter += 1
            if self.fetch_counter > MAXIMUM_FETCHES:
                raise BoomException('BOOM!')
            # elif randint(0, 3) == 0:
            #     raise Exception('Random generic exception')

            async with session.get(url) as response:
                return await response.read()


async def souper(data):
    soup = BeautifulSoup(data, features="html.parser")

    for link in soup.find_all('a'):
        print(link.get('href'))


async def get_comments_of_top_stories(loop, session, limit, iteration):
    """Retrieve top stories in HN.
    """
    fetcher = URLFetcher()  # create a new fetcher for this task
    try:
        data = await fetcher.fetch(session, TOP_STORIES_URL)
        data = data.decode('utf-8', 'replace')
    except Exception as e:
        log.error("Error retrieving top stories: {}".format(e))
        raise

    tasks = [souper(data)]
    results = await asyncio.gather(*tasks)
    return results

    #     loop, session, fetcher, post_id) for post_id in response[:limit]]

    # tasks = [post_number_of_comments(
    #     loop, session, fetcher, post_id) for post_id in response[:limit]]
    #
    # try:
    #     results = await asyncio.gather(*tasks)
    # except Exception as e:
    #     log.error("Error retrieving comments for top stories: {}".format(e))
    #     raise
    #
    # for post_id, num_comments in zip(response[:limit], results):
    #     log.info("Post {} has {} comments ({})".format(
    #         post_id, num_comments, iteration))
    # return fetcher.fetch_counter  # return the fetch count


# async def poll_top_stories_for_comments(loop, session, period, limit):
#     """Periodically poll for new stories and retrieve number of comments.
#     """
#     iteration = 1
#     errors = []
#     while True:
#         if errors:
#             log.info('Error detected, quitting')
#             return
#
#         log.info("Calculating comments for top {} stories. ({})".format(
#             limit, iteration))
#
#         future = asyncio.ensure_future(
#             get_comments_of_top_stories(loop, session, limit, iteration))
#
#         now = datetime.now()
#
#         def callback(fut):
#             try:
#                 fetch_count = fut.result()
#             except BoomException as e:
#                 log.debug('Adding {} to errors'.format(e))
#                 errors.append(e)
#             except Exception as e:
#                 log.exception('Unexpected error')
#                 errors.append(e)
#             else:
#                 log.info(
#                     '> Calculating comments took {:.2f} seconds and {} fetches'.format(
#                         (datetime.now() - now).total_seconds(), fetch_count))
#
#         future.add_done_callback(callback)
#
#         log.info("Waiting for {} seconds...".format(period))
#         iteration += 1
#         await asyncio.sleep(period)


if __name__ == '__main__':
    args = parser.parse_args()
    if args.verbose:
        log.setLevel(logging.DEBUG)

    loop = asyncio.get_event_loop()
    with aiohttp.ClientSession(loop=loop) as session:
        loop.run_until_complete(
            get_comments_of_top_stories(
                loop, session, args.period, args.limit))

    loop.close()
