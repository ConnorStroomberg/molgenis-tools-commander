import json

import requests

from mdev.configuration import get_config
from mdev.logging import get_logger

config = get_config()
log = get_logger()
token = ''


def login():
    global token

    login_url = config.get('api', 'login')
    username = config.get('auth', 'username')
    password = config.get('auth', 'password')

    log.debug('Logging in as user %s', username)

    response = post(login_url,
                    data={"username": username, "password": password})
    token = response.json()['token']


def get(url):
    return _handle_request(lambda: requests.get(url,
                                                headers={'Content-Type': 'application/json',
                                                         'x-molgenis-token': token}))


def post(url, data):
    return _handle_request(lambda: requests.post(url,
                                                 headers={'Content-Type': 'application/json',
                                                          'x-molgenis-token': token},
                                                 data=json.dumps(data)))


def _handle_request(request):
    response = str()
    try:
        response = request()
        response.raise_for_status()
        return response
    except requests.HTTPError as e:
        if 'application/json' in response.headers.get('Content-Type'):
            if 'errors' in response.json():
                for error in response.json()['errors']:
                    log.error(error['message'])
                exit(1)
        log.error(e)
        exit(1)
    except requests.RequestException as e:
        log.error(e)
        exit(1)
