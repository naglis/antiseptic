import logging
import re
import json

from abc import abstractmethod, ABCMeta

from .utils import diff

LOG = logging.getLogger(__name__)


class Cleaner(metaclass=ABCMeta):

    @abstractmethod
    def clean(self, title):
        pass


class RegexCleaner(Cleaner):
    name = 'regex'

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
                    try:
                        p = re.compile(rule['rule'])
                    except:
                        LOG.warning('Rule: %s failed to compile' % rule['id'])
                    else:
                        rule['pattern'] = p
                        self.rules.append(rule)
                    finally:
                        rule_ids.add(rule['id'])

        self.rules = sorted(self.rules, key=lambda x: x.get('weight', 0))

    def clean(self, title):
        for rule in self.rules:
            applied, new_title = RegexCleaner.apply_rule(rule, title)
            if not applied:
                continue
            d = ''.join(diff(title, new_title))
            LOG.debug('Applied rule: {rule_id:s}, diff:\n{diff:s}'.format(
                      rule_id=rule['id'], diff=d))
            title = new_title

        return title

    @staticmethod
    def apply_rule(rule, text):
        m = rule['pattern'].search(text)
        if m:
            return True, rule['pattern'].sub(rule.get('sub', ''), text)
        return False, text


try:
    import guessit
except ImportError:
    pass
else:
    class GuessitCleaner(Cleaner):
        name = 'guessit'

        def clean(self, title):

            guess = guessit.guess_movie_info(title)
            if 'title' in guess and 'year' in guess:
                tpl = '{title:} ({year:})'
            elif 'title' in guess:
                tpl = '{title:}'
            else:
                LOG.warning('Unable to determine title: {0:}'.format(title))
                return
            return tpl.format(**guess)
