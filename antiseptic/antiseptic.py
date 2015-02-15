import argparse
import errno
import json
import logging
import os
import sys
from collections import OrderedDict

from .cleaner import RegexCleaner
from .utils import (
    check_latest,
    get_config,
    get_new_rules,
    green,
    list_dirs,
    list_files,
    prompt,
)

GUESSIT = True
try:
    from .cleaner import GuessitCleaner
except ImportError:
    GUESSIT = False

__progname__ = 'antiseptic'
__version__ = '0.1.2'
__author__ = 'Naglis Jonaitis'
__email__ = 'njonaitis@gmail.com'
__description__ = 'A simple movie directory name cleaner'

LOG = logging.getLogger(__name__)
CONSOLE_MESSAGE_FORMAT = '%(message)s'
LOG_FILE_MESSAGE_FORMAT = '[%(asctime)s] %(levelname)-8s %(name)s %(message)s'
DEFAULT_VERBOSE_LEVEL = 1


def setup_cleaners(args, config):
    cleaners = {}

    disabled = set(config.get('disabled_rules', []))
    if disabled:
        LOG.info('Disabled rules: %s' % (', '.join(disabled)))
    rules_filename = config['rules_filename']

    c = RegexCleaner(disabled=disabled)
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
        cleaners[1] = c

    if GUESSIT:
        priority = 0 if args.prefer_guessit else 10
        cleaners[priority] = GuessitCleaner()

    return [cleaners[k] for k in sorted(cleaners.keys())]


def operate_helper(path, cleaners, action='rename', dry_run=False,
                   default_choice='n', auto=False):

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

    if action == 'rename':
        f = rename
    else:
        f = wrap

    path = os.path.normpath(path)
    base, old_name = os.path.split(path)
    if action == 'rename':
        name = old_name
    else:
        name, _ = os.path.splitext(old_name)

    new_names = OrderedDict()
    for c in cleaners:
        new_names[c.name] = c.clean(name)

    LOG.info('{0:s}: {1:s}'.format(
        action == 'rename' and 'Renaming' or 'Wraping', path))
    print('Old name: {0:s}'.format(old_name))
    print(action == 'rename' and 'New names:' or 'Directory names:')
    for i, (c, n) in enumerate(new_names.items(), start=1):
        print('{0:d}) [{1:s}] {2:s}'.format(i, green(c), n))

    if dry_run:
        print()
        return
    elif auto:
        f(path, new_names[list(new_names.keys())[0]])
        return

    choice_nums = list(map(str, range(1, len(new_names.keys()) + 1)))
    choice = prompt(action == 'rename' and 'Rename' or 'Wrap',
                    choice_nums + ['n', 'q'], default_choice)
    if choice == 'q':
        sys.exit(0)
    elif choice in choice_nums:
        f(path, new_names[list(new_names.keys())[int(choice) - 1]])
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

    cleaners = setup_cleaners(args, config)

    if args.directory:
        for dn in list_dirs(args.path):
            operate_helper(dn, cleaners, dry_run=args.dry_run,
                           default_choice=args.choice, auto=args.auto)
    else:
        operate_helper(args.path, cleaners, dry_run=args.dry_run,
                       default_choice=args.choice, auto=args.auto)


def do_wrap(args, config):
    """Wrap an existing movie inside a directory with a clean name"""
    if args.directory and not os.path.isdir(args.path):
        raise SystemExit(
            'Path "%s" does not exist or is not a directory' % args.path)
    elif not args.directory and not os.path.isfile(args.path):
        raise SystemExit(
            'File "%s" does not exist or is not a file' % args.path)

    cleaners = setup_cleaners(args, config)
    if args.directory:
        for fp in list_files(args.path):
            operate_helper(fp, cleaners, action='wrap', dry_run=args.dry_run,
                           default_choice=args.choice, auto=args.auto)
    else:
        operate_helper(args.path, cleaners, action='wrap',
                       dry_run=args.dry_run, default_choice=args.choice,
                       auto=args.auto)


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
        '-y', '--yes', action='store_const', const='1', default='n',
        dest='choice', help='make the prefered cleaner the default choice')
    common_parser.add_argument('-g', '--guessit', action='store_true',
                               dest='prefer_guessit',
                               help='prefer guessit renamer (if available)')
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
