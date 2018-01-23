#!/usr/bin/python3

import logging
import re

import suse_msg.meta as meta


def format_xterm(text, fg=None, bg=None):
    def seq(s):
        return "\x1B[%sm" % ';'.join(map(str, s))
    colors = {
        'black':        [30],
        'darkgray':     [30, 1],
        'red':          [31],
        'lightred':     [31, 1],
        'green':        [32],
        'lightgreen':   [32, 1],
        'yellow':       [33],
        'lightyellow':  [33, 1],
        'blue':         [34],
        'lightblue':    [34, 1],
        'magenta':      [35],
        'lightmagenta': [35, 1],
        'cyan':         [36],
        'lightcyan':    [36, 1],
        'gray':         [37],
        'lightgray':    [37, 1],
    }
    seqs = []
    if fg:
        seqs.extend(colors[fg])
    if bg:
        if len(colors[bg]) == 1:
            seqs.append(colors[bg][0] + 10)
    return seq(seqs) + text + seq([0])


def format_irc(text, fg=None, bg=None):
    def seq(fg, bg):
        s = "\x03"
        if fg != 99:
            s += "%01i" % fg
            if bg != 99:
                s += "%01i" % bg
        return s
    colors = {
        'lightgray':    0,
        'black':        1,
        'blue':         2,
        'green':        3,
        'lightred':     4,
        'red':          5,
        'magenta':      6,
        'yellow':       7,
        'lightyellow':  8,
        'lightgreen':   9,
        'cyan':         10,
        'lightcyan':    11,
        'lightblue':    12,
        'lightmagenta': 13,
        'darkgray':     14,
        'gray':         15,
    }
    fg = colors[fg] if fg else 99
    bg = colors[bg] if bg else 99
    return seq(fg, bg) + text + seq(99, 99)


def format_txt(text, fg=None, bg=None):
    return text


colorizers = {
    'xterm': format_xterm,
    'irc': format_irc,
    'txt': format_txt,
}


class MsgFormatter(object):
    def __init__(self, hide_raw=False):
        self.hide_raw = hide_raw
        self.processors = {}
        for processor in meta.get_processors():
            logging.info("Loading processor '%s'" % processor.__name__)
            self.processors[re.compile(processor.topic_regex)] = processor

    def fmt(self, topic, msg, colors='irc'):
        colorizer = colorizers[colors]
        for rtopic, processor in self.processors.items():
            if rtopic.match(topic):
                return processor(topic, msg).fmt(colorizer)
        logging.warning("no processor for topic %s" % topic)
        if not self.hide_raw:
            return '%s -> %s' % (topic, msg)
