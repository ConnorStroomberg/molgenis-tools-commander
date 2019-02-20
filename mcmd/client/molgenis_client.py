import json
from enum import Enum
from urllib.parse import urljoin

import requests

from mcmd.client import auth
from mcmd.config import config
from mcmd.logging import get_logger
from mcmd.utils.utils import McmdError

log = get_logger()


class ResourceType(Enum):
    ENTITY_TYPE = ('sys_md_EntityType', 'entityclass', 'Entity Type')
    THEME = ('sys_set_StyleSheet', 'stylesheet', 'Stylesheet')
    PACKAGE = ('sys_md_Package', 'package', 'Package')
    PLUGIN = ('sys_Plugin', 'plugin', 'Plugin')

    def get_entity_id(self):
        return self.value[0]

    def get_resource_name(self):
        return self.value[1]

    def get_label(self):
        return self.value[2]

    @classmethod
    def of_label(cls, label):
        return ResourceType[label.replace(' ', '_').upper()]


class PrincipalType(Enum):
    USER = 'user'
    ROLE = 'role'


def request(func):
    def handle_json_error(response_json):
        if 'errors' in response_json:
            for error in response_json['errors']:
                raise McmdError(error['message'])
        elif 'errorMessage' in response_json:
            raise McmdError(response_json['errorMessage'])

    def is_json(response):
        return response.headers.get('Content-Type') and 'application/json' in response.headers.get('Content-Type')

    def token_is_valid(response):
        """There's no real way to figure out if a token exists or is valid. The best we can do is assume that any
        'no read metadata' error means that the user isn't logged in."""
        if response.status_code == 401 and is_json(response):
            error = response.json()['errors'][0]
            if 'code' in error and error['code'] == 'DS04' and 'message' in error and error['message'].startswith(
                    "No 'Read metadata' permission"):
                return False
        return True

    def handle_request(*args, **kwargs):
        response = str()
        try:
            response = func(*args, **kwargs)
            response.raise_for_status()
            return response
        except requests.HTTPError as e:
            if not token_is_valid(response):
                auth.login()
                handle_request(*args, **kwargs)
            if is_json(response):
                handle_json_error(response.json())
            raise McmdError(str(e))
        except requests.RequestException as e:
            raise McmdError(str(e))

    return handle_request


@request
def get(url):
    return requests.get(url,
                        headers=_get_default_headers())


@request
def grant(principal_type, principal_name, resource_type, identifier, permission):
    data = {'radio-' + identifier: permission}

    if principal_type == PrincipalType.USER:
        data['username'] = principal_name
    elif principal_type == PrincipalType.ROLE:
        data['rolename'] = principal_name.upper()
    else:
        raise McmdError('Unknown principal type: %s' % principal_type)

    url = config.api('perm') + resource_type.get_resource_name() + '/' + principal_type.value
    return requests.post(url,
                         headers={
                             'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                             'x-molgenis-token': auth.get_token()},
                         data=data)


@request
def post(url, data):
    return requests.post(url,
                         headers=_get_default_headers(),
                         data=json.dumps(data))


@request
def post_file(url, file_path, params):
    return requests.post(url,
                         headers={'x-molgenis-token': auth.get_token()},
                         files={'file': open(file_path, 'rb')},
                         params=params)


@request
def post_files(files, url):
    return requests.post(url,
                         headers={'x-molgenis-token': auth.get_token()},
                         files=files)


@request
def delete(url):
    return requests.delete(url,
                           headers=_get_default_headers())


@request
def delete_data(url, data):
    return requests.delete(url,
                           headers=_get_default_headers(),
                           data=json.dumps({"entityIds": data}))


@request
def put(url, data):
    return requests.put(url=url,
                        headers=_get_default_headers(),
                        data=data)


@request
def import_by_url(params):
    return requests.post(config.api('import_url'),
                         headers=_get_default_headers(),
                         params=params)


def _get_default_headers():
    headers = {'Content-Type': 'application/json',
               'x-molgenis-token': auth.get_token()}
    return headers


def resource_exists(resource_id, resource_type):
    log.debug('Checking if %s %s exists' % (resource_type.get_label(), resource_id))
    response = get(config.api('rest2') + resource_type.get_entity_id() + '?q=id==' + resource_id)
    return int(response.json()['total']) > 0


def one_resource_exists(resources, resource_type):
    log.debug('Checking if one of [{}] exists in [{}]'.format(','.join(resources), resource_type.get_label()))
    response = get(config.api('rest2') + resource_type.get_entity_id() + '?q=id=in=({})'.format(','.join(resources)))
    return int(response.json()['total']) > 0


def ensure_resource_exists(resource_id, resource_type):
    if not resource_exists(resource_id, resource_type):
        raise McmdError('No %s found with id %s' % (resource_type.get_label(), resource_id))


def ensure_principal_exists(principal_name, principal_type):
    if not principal_exists(principal_name, principal_type):
        raise McmdError('No {} found with id {}'.format(principal_type.value, principal_name))


def principal_exists(principal_name, principal_type):
    if principal_type == PrincipalType.USER:
        return user_exists(principal_name)
    elif principal_type == PrincipalType.ROLE:
        return role_exists(principal_name)
    else:
        raise McmdError('Unknown principal type: %s' % principal_type)


def get_version():
    response = get(urljoin(config.api('rest2'), 'version'))
    return response.json()['molgenisVersion']


def user_exists(username):
    log.debug('Checking if user %s exists' % username)
    response = get(config.api('rest2') + 'sys_sec_User?q=username==' + username)
    return int(response.json()['total']) > 0


def role_exists(rolename):
    log.debug('Checking if role %s exists' % rolename)
    response = get(config.api('rest2') + 'sys_sec_Role?q=name==' + rolename.upper())
    return int(response.json()['total']) > 0
