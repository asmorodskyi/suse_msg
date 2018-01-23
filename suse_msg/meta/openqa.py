#!/usr/bin/python3

import re

from suse_msg.meta import BaseProcessor


class OpenQAProcessor(BaseProcessor):
    topic_regex = r"(?P<scope>[^.]+)\.openqa\.(?P<object>[^.]+)\.(?P<event>[^.]+)"

    def prepare(self):
        m = re.match(type(self).topic_regex, self.topic)
        self.scope = m.group('scope')
        self.object = m.group('object')
        self.event = m.group('event')

    def fmt(self, c):
        s = ""

        if self.object == 'job':
            s = "GROUP %s |TEST %s |" % (self.msg['group_id'], self.msg['TEST'])
            if self.event == 'done':
                s += self.colored_job_result(c)
            s += ": " + self.job_url()
        else:
            s += "UNSUPPORTED!"
        return s

    def colored_job_result(self, c):
        if 'result' not in self.msg:
            return 'n/a'
        color = {
            "failed": "lightred",
            "parallel_failed": "yellow",
            "softfailed": "lightyellow",
            "passed": "lightgreen",
            "obsoleted": "blue",
            "user_cancelled": "red",
            "incomplete": "red",
        }.get(self.msg['result'], None)
        return c(self.msg['result'], color)

    def event_past_perfect(self):
        return {
            "create": "created",
            "update": "updated",
            "delete": "deleted",
            "cancel": "canceled",
            "restart": "restarted",
            "duplicate": "duplicated",
            "done": "finished",
        }.get(self.event, '%sed' % self.event)

    def job_url(self):
        return self.base_url() + "t%i" % int(self.msg['id'])

    def comment_url(self):
        if self.is_group_event():
            path = "group_overview/%i" % int(self.msg['group_id'])
        elif self.is_job_event():
            path = "t%i" % int(self.msg['job_id'])
        return "%s%s#comment-%i" % (self.base_url(), path, int(self.msg['id']))

    def is_group_event(self):
        return bool(self.msg.get('group_id'))

    def is_job_event(self):
        return bool(self.msg.get('job_id'))

    def base_url(self):
        if self.scope == 'suse':
            return 'https://openqa.suse.de/'
        elif self.scope == 'opensuse':
            return 'https://openqa.opensuse.org/'
