#!/usr/bin/python3

import json
import logging
import os
import argparse
import sys
import time
import fcntl

import pika

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))
from suse_msg.ircclient import IRCClient
from suse_msg.router import Router
from suse_msg.msgfmt import MsgFormatter

logging.basicConfig(level=logging.INFO)
parser = argparse.ArgumentParser()
parser.add_argument('--config', choices=['osd', 'o3'], required=True)
args = parser.parse_args()

if args.config == 'osd':
    my_osd_groups = [170, 117]
    config = {
        "routing": {
            "#asmorodskyi-notify": [
                ("suse.openqa.job.done", lambda t, m: m.get('result', "")
                 == "failed" and m.get('group_id', "") in my_osd_groups),
                ("suse.openqa.job.done", lambda t, m: m.get('result', "")
                 == "failed" and m.get('TEST') == "trinity")
            ]
        }
    }
    amqp_server = "amqps://suse:suse@rabbit.suse.de"
    bot_name = "hermes_osd"
    pid_file = '/tmp/suse_msg_osd.lock'
else:
    config = {
        "routing": {
            "#asmorodskyi-notify": [
                ("suse.openqa.job.done", lambda t, m: m.get('result', "")
                 == "failed" and m.get('TEST').startswith("wicked_basic_"))
            ]
        }
    }
    amqp_server = "amqps://opensuse:opensuse@rabbit.opensuse.org"
    bot_name = "hermes_o3"
    pid_file = '/tmp/suse_msg_o3.lock'


router = Router(config['routing'])
formatter = MsgFormatter()

ircc = IRCClient("irc.suse.de", 6697, bot_name, router.channels)


def msg_cb(ch, method, properties, body):
    topic = method.routing_key
    try:
        body = body.decode("UTF-8")
        msg = json.loads(body)
    except ValueError:
        logging.warning("Invalid msg: %r -> %r" % (topic, body))
    else:
        print("%s: %s" % (topic, formatter.fmt(topic, msg, colors='xterm')))
        ircc.privmsg(formatter.fmt(topic, msg),
                     router.target_channels(topic, msg))


while True:
    try:
        fp = open(pid_file, 'w')
        try:
            logging.info("Check if another instance is running ....")
            fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            sys.exit(0)
        logging.info("Connecting to AMQP server")
        connection = pika.BlockingConnection(pika.URLParameters(amqp_server))
        channel = connection.channel()

        channel.exchange_declare(
            exchange="pubsub", exchange_type='topic', passive=True, durable=True)

        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue

        for binding_key in router.keys:
            channel.queue_bind(exchange="pubsub",
                               queue=queue_name, routing_key=binding_key)

        channel.basic_consume(msg_cb, queue=queue_name, no_ack=True)

        logging.info("Connected")
        channel.start_consuming()
    except pika.exceptions.AMQPConnectionError as e:
        logging.warning("AMQP Connection failed: %s" % e)
        time.sleep(5)
