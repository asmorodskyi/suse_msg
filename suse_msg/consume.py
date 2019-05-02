#!/usr/bin/python3

from suse_msg.router import Router
import json
import logging
import os
import argparse
import sys
import time
import fcntl

import smtplib
import pika

logging.basicConfig(level=logging.INFO)
parser = argparse.ArgumentParser()
parser.add_argument('--server', choices=['osd', 'o3'], required=True)
args = parser.parse_args()

if args.server == 'osd':
    my_osd_groups = [170, 117]
    rules = [
        ("suse.openqa.job.done", lambda t, m: m.get('result', "")
         == "failed" and m.get('group_id', "") in my_osd_groups),
        ("suse.openqa.job.done", lambda t, m: m.get('result', "")
         == "failed" and m.get('TEST') == "trinity")
    ]
    amqp_server = "amqps://suse:suse@rabbit.suse.de"
    bot_name = "hermes_osd"
    pid_file = '/tmp/suse_msg_osd.lock'
else:
    rules = [
        ("suse.openqa.job.done", lambda t, m: m.get('result', "")
         == "failed" and m.get('TEST').startswith("wicked_basic_")),
         ("suse.openqa.job.done", lambda t, m: True )
    ]
    amqp_server = "amqps://opensuse:opensuse@rabbit.opensuse.org?heartbeat_interval=5"
    bot_name = "hermes_o3"
    pid_file = '/tmp/suse_msg_o3.lock'


router = Router(rules)
sender = 'asmorodskyi@suse.com'
receivers = ['asmorodskyi@suse.com']
smtpObj = smtplib.SMTP('relay.suse.de', 25)


def msg_cb(ch, method, properties, body):
    topic = method.routing_key
    try:
        body = body.decode("UTF-8")
        msg = json.loads(body)
        if router.is_matched(topic,msg):
            print("%s: %s" % (topic, msg))
            email = '''\
Subject: [Openqa-Notify] {subject}
From: {_from}
To: {_to}


{message}
'''.format(subject=topic, _from=sender, _to=receivers, message=msg)
            smtpObj.sendmail(sender, receivers, email)
    except ValueError:
        logging.warning("Invalid msg: %r -> %r" % (topic, body))


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
