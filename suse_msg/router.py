#!/usr/bin/python3

import re

class Router(object):
    def __init__(self, rules):
        self.keys = set()
        self.rules = []
        for rule in rules:
            if isinstance(rule, str):
                self.rules.append((self.key_to_regex(rule), lambda t, m: True))
            elif isinstance(rule, tuple):
                self.rules.append((self.key_to_regex(rule[0]), rule[1]))

    def key_to_regex(self, key):
        self.keys.add(key)
        return re.compile(key.replace('.', '\.').replace('*', '[^.]*').replace('#', '.*'))


    def is_matched(self, topic, msg):
        for rule in self.rules:
            rkey, filter_matches = rule
            if rkey.match(topic) and filter_matches(topic, msg):
                return True
