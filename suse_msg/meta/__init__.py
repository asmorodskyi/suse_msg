#!/usr/bin/python3

import inspect
import os
from importlib import import_module


class BaseProcessor(object):
    topic_regex = r""

    def __init__(self, topic, msg):
        self.topic = topic
        self.msg = msg
        self.prepare()

    def prepare(self):
        pass

    def fmt(self, c):
        raise Exception()


def get_processors():
    for module in os.listdir(os.path.dirname(__file__)):
        if module == '__init__.py' or module[-3:] != '.py':
            continue
        m = import_module('suse_msg.meta.%s' % module[:-3])
        for name, obj in inspect.getmembers(m):
            if inspect.isclass(obj) and issubclass(obj, BaseProcessor) and obj is not BaseProcessor:
                yield obj
