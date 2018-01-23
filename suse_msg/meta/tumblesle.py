import logging
import re
from collections import deque

from suse_msg.meta import BaseProcessor

logging.basicConfig(level=logging.INFO)


# limit is 512 including all characters, just split it somewhere. 400 seems
# to be a sensible value. Reduce it further to limit the line of messages
# pumped out to users in IRC. Reduced *even more* to act as a workaround by
# limiting the strings so much that there will probably be only one message
# per build about regressions unless there is a status change
MSG_LIMIT = 12

# limit of how many times a truncated message has to show up the same before we repeat it
SEEN_LIMIT = 4
SEEN = deque(maxlen=SEEN_LIMIT)

def truncate(s):
    if len(s) > MSG_LIMIT:
        s = s[0:MSG_LIMIT] + '…'
    return s


def comma_entries(l):
    if type(l) is not list:
        return l
    return ', '.join(l)


class TumbleSLEProcessor(BaseProcessor):
    topic_regex = r"(?P<scope>[^.]+)\.tumblesle\.(?P<event>[^.]+)"

    def prepare(self):
        m = re.match(type(self).topic_regex, self.topic)
        self.scope = m.group('scope')
        self.event = m.group('event')

    def fmt(self, c):
        result = self.colored_result(c)
        # prevent irc.client.MessageTooLong
        msg = ', '.join('%s: %s' % (k, truncate(comma_entries(v))) for k, v in self.msg.items())
        s = "tumbleSLE %s: %s" % (result, msg)
        if s in SEEN:
            logging.info("Ignoring already seen message '%s'" % s)
            return ''
        else:
            logging.info("not found s in self.seen. self.seen: %s" % SEEN)
        SEEN.append(s)
        return s

    def colored_result(self, c):
        color = {
            "regression": "lightred",
            "release": "lightgreen",
        }.get(self.event, None)
        return c(self.event, color)
