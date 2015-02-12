import argparse
import errno
import json
import logging
import os
import re
import sys

from .utils import (
    check_latest,
    diff,
    get_config,
    get_new_rules,
    list_dirs,
    list_files,
    prompt,
)

__progname__ = 'antiseptic'
__version__ = '0.1.2'
__author__ = 'Naglis Jonaitis'
__email__ = 'njonaitis@gmail.com'
__description__ = 'A simple movie directory name cleaner'

LOG = logging.getLogger(__name__)
CONSOLE_MESSAGE_FORMAT = '%(message)s'
LOG_FILE_MESSAGE_FORMAT = '[%(asctime)s] %(levelname)-8s %(name)s %(message)s'
DEFAULT_VERBOSE_LEVEL = 1


class Cleaner(object):

    def __init__(self, disabled=None):
        self.rules = []
        if disabled is None:
            disabled = set()
        self.disabled = disabled

    def load_rules(self, filename):
        rule_ids = set()

        with open(filename) as f:
            data = json.load(f)

            if 'rules' not in data:
                raise SystemExit('No rules in the rule file')

            rules = data.get('rules')

            for rule in rules:
                if 'id' not in rule:
                    LOG.warning('Missing rule ID: %s' % rule)
                    continue

                if rule['id'] in self.disabled:
                    continue

                if rule['id'] in rule_ids:
                    LOG.warning('Duplicate rule with ID: %s' % rule['id'])
                    continue
                else:
                    self.rules.append(rule)
                    rule_ids.add(rule['id'])

        self.rules = sorted(self.rules, key=lambda x: x.get('weight', 0))

    def clean_title(self, title):
        applied_rules = []
        for rule in self.rules:
            applied, new_title = Cleaner.apply_rule(rule, title)
            if not applied:
                continue
            applied_rules.append(rule['id'])
            d = ''.join(diff(title, new_title))
            LOG.debug('Applied rule: {rule_id:s}, diff:\n{diff:s}'.format(
                      rule_id=rule['id'], diff=d))
            title = new_title

        return title, applied_rules

    @staticmethod
    def apply_rule(rule, text):
        m = re.search(rule['rule'], text)
        if m:
            return True, re.sub(rule['rule'], rule.get('sub', ''), text)
        return False, text


def setup_cleaner(config):
    disabled = set(config.get('disabled_rules', []))
    if disabled:
        LOG.info('Disabled rules: %s' % (', '.join(disabled)))
    rules_filename = config['rules_filename']

    c = Cleaner(disabled=disabled)
    try:
        c.load_rules(rules_filename)
    except OSError as e:
        if e.errno == errno.ENOENT:
            raise SystemExit('The rules file: %s does not exist. '
                             'Run `antiseptic update` to update the rules.' %
                             rules_filename)
        else:
            raise
    else:
        return c


def rename_dir(path, cleaner, dry_run=False, default_choice='n', auto=False):

    def rename(path, new_name):
        base, _ = os.path.split(path)
        try:
            new_path = os.path.join(base, new_name)
            LOG.debug('Renaming: {path:s} to {new_path:s}'.format(
                path=path, new_path=new_path))
            os.rename(path, new_path)
        except OSError as e:
            LOG.exception(e)
            return
        else:
            LOG.info('Renamed successfully.')

    path = os.path.normpath(path)
    base, old_name = os.path.split(path)
    new_name, rules = cleaner.clean_title(old_name)

    if new_name == old_name:
        LOG.debug('Nothing to be done.')
        return

    LOG.info('Applied rules: %s' % ', '.join(rules))
    print(''.join(diff(old_name, new_name)))

    if dry_run:
        print()
        return
    elif auto:
        rename(path, new_name)
        return

    choice = prompt('Apply', ['y', 'n', 'q'], default_choice)
    if choice == 'q':
        sys.exit(0)
    elif choice == 'y':
        rename(path, new_name)
    else:
        return


def wrap_file(path, cleaner, dry_run=False, default_choice='n', auto=False):

    def wrap(path, dir_name):
        base, fname = os.path.split(path)
        new_dir_path = os.path.join(base, dir_name)
        new_file_path = os.path.join(new_dir_path, fname)
        try:
            LOG.debug('Creating a new directory: {0:s}'.format(new_dir_path))
            os.mkdir(new_dir_path)
            LOG.debug('Moving: {path:s} to {new_file_path:s}'.format(
                path=path, new_file_path=new_file_path))
            os.rename(path, new_file_path)
        except OSError as e:
            LOG.exception(e)
            return
        else:
            LOG.info('Wraped successfully.')

    path = os.path.normpath(path)
    base, old_name = os.path.split(path)
    name, ext = os.path.splitext(old_name)
    dir_name, rules = cleaner.clean_title(name)

    LOG.info('Wrapping: {0:s}'.format(path))
    LOG.info('Applied rules: {0:s}'.format(', '.join(rules)))
    print('New directory name: {0:s}'.format(dir_name))

    if dry_run:
        print()
        return
    elif auto:
        wrap(path, dir_name)
        return

    choice = prompt('Wrap', ['y', 'n', 'q'], default_choice)
    if choice == 'q':
        sys.exit(0)
    elif choice == 'y':
        wrap(path, dir_name)
    else:
        return


def do_check(args, config):
    up_to_date, latest_version = check_latest(
        config['rules_filename'], config['update_server'])
    if up_to_date:
        LOG.info('You have the latest version of the rules.')
    else:
        LOG.warning('A newer version (%s) is available. '
                    'Type `antiseptic update` to update' % latest_version)


def do_update(args, config):
    up_to_date, latest_version = check_latest(
        config['rules_filename'], config['update_server'])
    if not args.force and up_to_date:
        LOG.info('You already have the latest version of the rules.')
        return

    rules_filename = config['rules_filename']
    if os.path.exists(rules_filename):
        with open(rules_filename) as f:
            try:
                old_rules = json.load(f).get('rules', [])
            except ValueError:
                LOG.warning('Failed to load the old rules.')
                old_rules = []
    else:
        old_rules = []

    custom_rules = list(filter(lambda r: r['id'].startswith('_'), old_rules))
    if custom_rules:
        LOG.debug('%d custom rules found.' % len(custom_rules))

    new_data = get_new_rules(config['update_server'])
    for cr in custom_rules:
        new_data['rules'].append(cr)

    with open(rules_filename, 'w') as f:
        json.dump(new_data, f, indent='\t', sort_keys=True)
    LOG.info('The rules were successfully updated.')


def do_rename(args, config):
    if not os.path.isdir(args.path):
        raise SystemExit(
            'Path "%s" does not exist or is not a directory' % args.path)

    cleaner = setup_cleaner(config)

    if args.directory:
        for dn in list_dirs(args.path):
            rename_dir(dn, cleaner, dry_run=args.dry_run,
                       default_choice=args.choice, auto=args.auto)
    else:
        rename_dir(args.path, cleaner, dry_run=args.dry_run,
                   default_choice=args.choice, auto=args.auto)


def do_wrap(args, config):
    """Wrap an existing movie inside a directory with a clean name"""
    if args.directory and not os.path.isdir(args.path):
        raise SystemExit(
            'Path "%s" does not exist or is not a directory' % args.path)
    elif not args.directory and not os.path.isfile(args.path):
        raise SystemExit(
            'File "%s" does not exist or is not a file' % args.path)

    cleaner = setup_cleaner(config)
    if args.directory:
        for fp in list_files(args.path):
            wrap_file(fp, cleaner, dry_run=args.dry_run,
                      default_choice=args.choice, auto=args.auto)
    else:
        wrap_file(args.path, cleaner, dry_run=args.dry_run,
                  default_choice=args.choice, auto=args.auto)


def main():
    p = argparse.ArgumentParser(prog=__progname__, description=__description__)
    p.add_argument('--version', action='version',
                   version='%(prog)s ' + __version__)
    p.add_argument(
        '-d', '--debug', action='store_true',
        help='output debug information')
    p.add_argument(
        '-v', '--verbose', action='count', dest='verbose_level',
        default=DEFAULT_VERBOSE_LEVEL,
        help='increase verbosity of output. Can be repeated.',)
    p.add_argument(
        '--log-file', action='store', default=None,
        help='specify a file to log output. Disabled by default.',)
    p.add_argument(
        '--quiet', action='store_const', dest='verbose_level',
        const=0, help='suppress output except warnings and errors',)
    subparsers = p.add_subparsers()

    # common arguments for rename and wrap
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('path', metavar='PATH')
    common_parser.add_argument(
        '-y', '--yes', action='store_const', const='y', default='n',
        dest='choice', help='make \'yes\' the default choice')
    # -n and -a can't be used together
    mutex_group = common_parser.add_mutually_exclusive_group()
    mutex_group.add_argument(
        '-n', '--dry-run', action='store_true',
        help='don\'t do anything, just preview the results')
    mutex_group.add_argument(
        '-a', '--auto', action='store_true',
        help='don\'t ask questions, rename everything automatically')

    rename_parser = subparsers.add_parser('rename', help='rename directories',
                                          parents=[common_parser])
    rename_parser.add_argument(
        '-d', '--dir', action='store_true', dest='directory',
        help='rename all directories inside PATH')
    rename_parser.set_defaults(func=do_rename)

    wrap_parser = subparsers.add_parser(
        'wrap', help='wrap a movie file inside a directory with a clean name',
        parents=[common_parser])
    wrap_parser.add_argument(
        '-d', '--dir', action='store_true', dest='directory',
        help='wrap all files inside PATH')
    wrap_parser.set_defaults(func=do_wrap)

    check_parser = subparsers.add_parser(
        'check', help='check for rule updates')
    check_parser.set_defaults(func=do_check)

    update_parser = subparsers.add_parser('update', help='update rules')
    update_parser.add_argument(
        '-f', '--force', action='store_true',
        help='force update even if already on the latest version')
    update_parser.set_defaults(func=do_update)

    args = p.parse_args()

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Set up logging to a file.
    if args.log_file:
        file_handler = logging.FileHandler(
            filename=args.log_file,
        )
        formatter = logging.Formatter(LOG_FILE_MESSAGE_FORMAT)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Always send higher-level messages to the console via stderr
    console = logging.StreamHandler(sys.stderr)
    console_level = {
        0: logging.WARNING,
        1: logging.INFO,
        2: logging.DEBUG,
    }.get(args.verbose_level, logging.DEBUG)
    console.setLevel(console_level)
    formatter = logging.Formatter(CONSOLE_MESSAGE_FORMAT)
    console.setFormatter(formatter)
    root_logger.addHandler(console)

    try:
        config = get_config()
        if hasattr(args, 'func'):
            getattr(args, 'func')(args, config)
        else:
            p.print_help()
    except Exception as err:
        if args.debug:
            LOG.exception(err)
            raise
        else:
            LOG.error(err)
            return 1
