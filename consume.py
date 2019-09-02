#!/usr/bin/python3

import json
import logging
import argparse
import sys
import time
import fcntl

import smtplib
import pika
import json
import re

logging.basicConfig(level=logging.INFO)


def is_matched(rules, topic, msg):
    for rule in rules:
        rkey, filter_matches = rule
        if rkey.match(topic) and filter_matches(topic, msg):
            return True


def groupID_to_name(id):
    if id == 170 or id == 262:
        return "Network"
    else:
        return id


def send_email(topic, msg):
    if topic == 'suse.openqa.job.done':
        subj_text = 'SUSE.DE - '
    else:
        subj_text = 'openSUSE.ORG - '
    job_json = json.loads(msg)
    subj_text += job_json['TEST'] + '-' + job_json['ARCH'] + '-' + groupID_to_name(job_json['group_id'])
    sender = 'asmorodskyi@suse.com'
    receivers = ['asmorodskyi@suse.com']
    smtpObj = smtplib.SMTP('relay.suse.de', 25)
    email = '''\
Subject: [Openqa-Notify] {subject}
From: {_from}
To: {_to}


Build={build}
Flavor={flavor}
Disk={disk}
JobID={jobID}
'''.format(subject=subj_text, _from=sender, _to=receivers, build=job_json['BUILD'], flavor=job_json['FLAVOR'], disk=job_json['HDD_1'], jobID=job_json['id'])
    smtpObj.sendmail(sender, receivers, email)


parser = argparse.ArgumentParser()
parser.add_argument('--server', choices=['osd', 'o3'], required=True)
args = parser.parse_args()
rules_compiled = []

if args.server == 'osd':
    my_osd_groups = [170, 117]
    binding_key = "suse.openqa.job.done"
    rules_defined = [
        (binding_key, lambda t, m: m.get('result', "")
         == "failed" and m.get('group_id', "") in my_osd_groups),
        (binding_key, lambda t, m: m.get('result', "")
         == "failed" and m.get('TEST') == "trinity")
    ]
    amqp_server = "amqps://suse:suse@rabbit.suse.de"
    pid_file = '/tmp/suse_msg_osd.lock'
else:
    binding_key = "opensuse.openqa.job.done"
    rules_defined = [
        (binding_key, lambda t, m: m.get('result', "")
         == "failed" and m.get('TEST').startswith("wicked_basic_"))
    ]
    amqp_server = "amqps://opensuse:opensuse@rabbit.opensuse.org?heartbeat_interval=5"
    pid_file = '/tmp/suse_msg_o3.lock'

for rule in rules_defined:
    rules_compiled.append((re.compile(rule[0].replace('.', '\.').replace('*', '[^.]*').replace('#', '.*')), rule[1]))


def msg_cb(ch, method, properties, body):
    topic = method.routing_key
    try:
        body = body.decode("UTF-8")
        msg = json.loads(body)
        if is_matched(rules_compiled, topic, msg):
            print("%s: %s" % (topic, msg))
            send_email(topic, msg)
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
        channel.exchange_declare(exchange="pubsub", exchange_type='topic', passive=True, durable=True)
        result = channel.queue_declare(exclusive=True)
        queue_name = result.method.queue
        channel.queue_bind(exchange="pubsub", queue=queue_name, routing_key=binding_key)
        channel.basic_consume(msg_cb, queue=queue_name, no_ack=True)
        logging.info("Connected")
        channel.start_consuming()
    except pika.exceptions.AMQPConnectionError as e:
        logging.warning("AMQP Connection failed: %s" % e)
        time.sleep(5)
