from os import path, listdir, getcwd
from os.path import splitext, join

from mdev.configuration import get_config
from mdev.logging import get_logger
from mdev.requests import login, get, post
from mdev.utils import lower_kebab

log = get_logger()
config = get_config()


def import_(args):
    if path.isfile(args.file):
        # TODO importing from an absolute path
        log.warn('Importing from an absolute path')
        exit(1)
    elif path.isfile(join(getcwd(), args.file)):
        # TODO importing from current directory
        log.warn('Importing from the current directory')
        exit(1)
    else:
        # importing from quick-folders
        if not config.has_option('datasets', 'git_root'):
            log.warn('Molgenis git root not set. Edit the mdev.ini file to include the test datasets.')

        paths_string = ''.join(config.get('datasets', 'git_paths').split())
        paths = paths_string.split(',')
        map(str.strip, paths)

        files = dict()
        for folder in paths:
            if not path.isdir(folder):
                log.warn('Folder %s is not a valid folder, skipping it...', folder)

            for file in listdir(folder):
                file_name = splitext(file)[0]
                files[file_name] = join(folder, file)

        print(files)

        if splitext(args.file)[0] in files:
            print(files[splitext(args.file)[0]])


def _import_file(file_path):
    pass


def make(args):
    login()
    group_name = _find_group(args.role)

    log.info('Making user %s a member of role %s', args.user, args.role.upper())
    url = config.get('api', 'member') % group_name
    post(url, {'username': args.user, 'roleName': args.role.upper()})


def _find_group(role):
    log.debug('Fetching groups')
    groups = get(config.get('api', 'rest2') + 'sys_sec_Group?attrs=name')
    role = lower_kebab(role)

    matches = {len(group['name']): group['name'] for group in groups.json()['items'] if role.startswith(group['name'])}

    if not matches:
        log.error('No group found for role %s', role.upper())
        exit(1)

    return matches[max(matches, key=int)]


def add(args):
    login()

    if args.type == 'user':
        _add_user(args.value)
    elif args.type == 'group':
        _add_group(args.value)
    else:
        raise ValueError('invalid choice for add: %s', args.type)


def _add_user(username):
    log.info('Adding user %s', username)

    post(config.get('api', 'rest1') + 'sys_sec_User',
         {'username': username,
          'password_': username,
          'Email': username + "@molgenis.org",
          'active': True})


def _add_group(name):
    log.info('Adding group %s', name)
    post(config.get('api', 'group'), {'name': name, 'label': name})


def run(args):
    print("run", args)
