#!/usr/bin/python3

import ssl
import sys
import threading

import irc.client


class IRCClient(irc.client.SimpleIRCClient):
    def __init__(self, server, port, nickname, join_channels=[]):
        irc.client.SimpleIRCClient.__init__(self)
        self.channels = join_channels
        ssl_factory = irc.connection.Factory(wrapper=ssl.wrap_socket)
        self.connect(server, port, nickname, connect_factory=ssl_factory)
        self.loop = threading.Thread(target=self.start)
        self.loop.setDaemon(True)
        self.loop.start()

    def on_welcome(self, connection, event):
        for channel in self.channels:
            if irc.client.is_channel(channel):
                connection.join(channel)

    def on_disconnect(self, connection, event):
        sys.exit(0)

    def notice(self, text, channels):
        if text and channels:
            self.connection.notice(','.join(channels), text)

    def privmsg(self, text, channels):
        if text and channels:
            self.connection.privmsg(','.join(channels), text)

    def quit(self):
        self.connection.quit("bye")
