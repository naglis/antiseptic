import copy
import difflib
import functools
import json
import logging
import os
import sys
import socket

from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

LOG = logging.getLogger(__name__)
HOME = os.environ.get('HOME')
DEFAULT_CONFIG_DIR = os.path.join(HOME, '.config')
DEFAULT_DATA_DIR = os.path.join(HOME, '.local', 'share')
DEFAULT_CONFIG = {
    'disabled_rules': [],
    'update_server': 'https://naglis.github.io/antiseptic/',
}


def split_rev(version):
    if not version.isdigit():
        raise ValueError('Invalid version: %s' % version)
    return int(str(version)[:8]), int(str(version[8:]))


def diff(before, after):
    d = difflib.Differ()
    return d.compare(['%s\n' % before], ['%s\n' % after])


def wrap_text(text, prefix='\033[1m', postfix='\033[0m', file=sys.stdout,
              endline=''):

    if file.isatty():
        return '%s%s%s%s' % (prefix, text, postfix, endline)
    else:
        return '%s%s' % (text, endline)
red = functools.partial(wrap_text, prefix='\033[91m', postfix='\033[0m')
bold = functools.partial(wrap_text, prefix='\033[1m', postfix='\033[0m')


class HTTPRequestError(Exception):
    pass


def request(url, headers=None, max_attempts=3, timeout=10):
    if not headers:
        headers = {}
    attempt = 0
    req = Request(url, headers=headers)
    while True:
        attempt += 1
        LOG.debug('Requesting URL: %s, attempt: %d' % (url, attempt))
        try:
            resp = urlopen(req, timeout=timeout)
            data = resp.read().decode('utf-8')
        except (HTTPError, URLError, socket.timeout, socket.gaierror) as e:
            if attempt < max_attempts:
                continue
            else:
                raise HTTPRequestError(e)
        else:
            return data


def check_latest(rules_filename, update_server):
    current_release_date, current_rev = 0, 0
    if os.path.exists(rules_filename):
        with open(rules_filename) as f:
            try:
                data = json.load(f)
                current_release_date, current_rev = split_rev(
                    data.get('version', '000000000'))
            except ValueError:
                LOG.warning('Failed to load the old rules.')

    LOG.debug('Checking for the latest version at %s' % update_server)
    try:
        latest = request('%s/latest' % update_server)
    except HTTPRequestError as e:
        LOG.exception(e)
        raise SystemExit('Failed to check for the latest version online')

    latest_release_date, latest_rev = split_rev(latest)

    if latest_release_date > current_release_date or \
            (latest_release_date == current_release_date and
                latest_rev > current_rev):
        return False, latest
    return True, latest


def get_new_rules(update_server):
    LOG.debug('Downloading latest rules')
    try:
        data = request('%s/rules.json' % update_server)
    except HTTPRequestError as e:
        LOG.exception(e)
        raise SystemExit('Failed to download latest rules')
    else:
        return json.loads(data)


def get_config_dir():
    if os.environ.get('XDG_CONFIG_DIR'):
        return os.environ.get('XDG_CONFIG_DIR')
    else:
        return DEFAULT_CONFIG_DIR


def get_data_dir():
    if os.environ.get('XDG_DATA_HOME'):
        return os.environ.get('XDG_DATA_HOME')
    else:
        return DEFAULT_DATA_DIR


def make_dirs(path):
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        raise SystemExit('Failed to create config dir: %s' % str(e))


def list_dirs(dirname):
    dp, dn, _ = next(os.walk(dirname))
    for n in dn:
        yield os.path.join(dp, n)


def prompt(question, choices, default, case_sensitive=False, color=True):
    c = copy.copy(choices)
    d = bold(default.upper())
    c[c.index(default)] = color and red(d) or d
    print('%s [%s]? ' % (question, '/'.join(c)))

    while True:
        r = input()
        if not case_sensitive:
            r = r.lower()

        if r not in choices and r.strip() != '':
            print('Invalid choice. Pick from: %s' % choices)
        else:
            if not r.strip():
                return default
            else:
                return r


def get_config():
    config_dir = os.path.join(get_config_dir(), 'antiseptic')
    if not os.path.isdir(config_dir):
        LOG.debug('Creating config dir: %s' % config_dir)
        make_dirs(config_dir)

    config = DEFAULT_CONFIG
    config_filename = os.path.join(config_dir, 'config.json')
    if os.path.isfile(config_filename):
        with open(config_filename) as f:
            LOG.debug('Loading configuration from file: %s' % config_filename)
            custom_config = json.load(f)
            config.update(custom_config)

    if not config.get('rules_filename'):
        data_dir = os.path.join(get_data_dir(), 'antiseptic')
        if not os.path.isdir(data_dir):
            LOG.debug('Creating data dir: %s' % data_dir)
            make_dirs(data_dir)

        config['rules_filename'] = os.path.join(data_dir, 'rules.json')
    return config
