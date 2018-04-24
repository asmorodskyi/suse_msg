#!/usr/bin/env python

import pika
import sys

connection = pika.BlockingConnection(pika.URLParameters("amqps://opensuse:opensuse@rabbit.opensuse.org?heartbeat_interval=5"))
channel = connection.channel()

channel.exchange_declare(exchange='pubsub', exchange_type='topic', passive=True, durable=True)

result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue

binding_keys = sys.argv[1:]
if not binding_keys:
    sys.stderr.write("Usage: %s [binding_key]...\n" % sys.argv[0])
    sys.stderr.write("\nTry using '#' as binding_key to get all events\n")
    sys.exit(1)

for binding_key in binding_keys:
    channel.queue_bind(exchange='pubsub',
                       queue=queue_name,
                       routing_key=binding_key)

print(' [*] Waiting for logs. To exit press CTRL+C')

def callback(ch, method, properties, body):
    print(" [x] %r:%r" % (method.routing_key, body))

channel.basic_consume(callback,
                      queue=queue_name,
                      no_ack=True)

channel.start_consuming()
