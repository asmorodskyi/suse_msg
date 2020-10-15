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
import traceback

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
        return str(id)


def send_email(topic, msg):
    if topic == 'suse.openqa.job.done':
        subj_text = 'SUSE.DE - '
        job_url = 'https://openqa.suse.de/t'
    else:
        subj_text = 'openSUSE.ORG - '
        job_url = 'https://openqa.opensuse.org/t'
    subj_text += "{}-{}-{}".format(msg['TEST'], msg['ARCH'], groupID_to_name(msg['group_id']))
    job_url += str(msg['id'])
    hdd = 'None'
    if 'HDD_1' in msg:
        hdd = msg['HDD_1']
    sender = 'asmorodskyi@suse.com'
    receivers = ['asmorodskyi@suse.com', 'cfamullaconrad@suse.de']
    smtpObj = smtplib.SMTP('relay.suse.de', 25)
    email = '''\
Subject: [Openqa-Notify] {subject}
From: {_from}
To: {_to}


Build={build}
Flavor={flavor}
Disk={disk}
JobID={jobURL}
'''.format(subject=subj_text, _from=sender, _to=receivers, build=msg['BUILD'], flavor=msg['FLAVOR'], disk=hdd, jobURL=job_url)
    smtpObj.sendmail(sender, receivers, email)


parser = argparse.ArgumentParser()
parser.add_argument('--server', choices=['osd', 'o3'], required=True)
args = parser.parse_args()
rules_compiled = []

if args.server == 'osd':
    my_osd_groups = [262, 219, 274, 275, 276]
    binding_key = "suse.openqa.job.done"
    rules_defined = [
        (binding_key, lambda t, m: m.get('result', "")
         == "failed" and m.get('group_id', "") in my_osd_groups)
    ]
    credentials = pika.PlainCredentials('suse', 'suse')
    parameters = pika.ConnectionParameters(host='rabbit.suse.de', credentials=credentials)
    pid_file = '/tmp/suse_msg_osd.lock'
else:
    binding_key = "opensuse.openqa.job.done"
    rules_defined = [
        (binding_key, lambda t, m: m.get('result', "")
         == "failed" and m.get('TEST').startswith("wicked_"))
    ]
    credentials = pika.PlainCredentials('opensuse', 'opensuse')
    parameters = pika.ConnectionParameters(host='rabbit.opensuse.org', credentials=credentials, heartbeat=5)
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
        connection = pika.BlockingConnection(parameters)
        channel = connection.channel()
        channel.exchange_declare(exchange="pubsub", exchange_type='topic')
        result = channel.queue_declare('', exclusive=True)
        queue_name = result.method.queue
        channel.queue_bind(exchange="pubsub", queue=queue_name, routing_key=binding_key)
        channel.basic_consume(queue=queue_name, on_message_callback=msg_cb, auto_ack=True)
        logging.info("Connected")
        channel.start_consuming()
    except Exception as e:
        traceback.print_exc()
        channel.stop_consuming()
        time.sleep(5)
