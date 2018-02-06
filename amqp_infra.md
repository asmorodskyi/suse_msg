The AMQP Infrastructure
=======================

The AMQP Server
---------------

Setting up the cli tool:

	zypper in rabbitmq-server-plugins
	rabbitmq-plugins enable rabbitmq_management
	systemctl restart rabbitmq-server
	wget http://localhost:15672/cli/rabbitmqadmin -O /usr/local/bin/rabbitmqadmin
	chmod +x /usr/local/bin/rabbitmqadmin


Creating a permanent exchange:

	rabbitmqadmin declare exchange name=pubsub type=topic durable=true auto_delete=false internal=false


Creating the readonly user (consumer):

	rabbitmqctl add_user tux linux
	rabbitmqctl set_permissions tux '^amq\.gen.*$' '^amq\.gen.*$' '^(amq\.gen.*|pubsub)$'


Creating a publisher user:

	rabbitmqctl add_user openqa secret
	rabbitmqctl set_permissions openqa '^amq\.gen.*$' '^(amq\.gen.*|pubsub)$' '^(amq\.gen.*|pubsub)$'


Publishing messages
-------------------

Make sure to do a **passive**, **durable** exchange_declare.
This will check if a suitable exchange exists on the server but raise
an error, if it doesn't exist. It will not try to create the exchange.
We do this because the user isn't allowed to create the exchange.
The server admin created a permanent exchange in the setup above.

```python
import pika, json
connection = pika.BlockingConnection(pika.URLParameters("amqp://openqa:secret@kazhua.suse.de"))
channel = connection.channel()
channel.exchange_declare(exchange='pubsub', exchange_type='topic', passive=True, durable=True)
def send_msg(topic, msg): 
	json_msg = json.dumps(msg)
	channel.basic_publish(exchange='pubsub', routing_key=topic, body=json_msg)
send_msg('suse.obs.comment.create', {"user": "foo", "comment": "bar", "id": 123}) 
connection.close()
```


Consuming messages
------------------

There are wildcards for matching topics:

- `#` matches everything
- `*` matches everything except a `.`

Make sure to do a **passive**, **durable** exchange_declare...
Also make sure to declare a **exclusive** queue to prevent
other users from accessing your queue.

```python
import pika, json
connection = pika.BlockingConnection(pika.URLParameters("amqp://tux:linux@kazhua.suse.de"))
channel = connection.channel()
channel.exchange_declare(exchange='pubsub', exchange_type='topic', passive=True, durable=True)
result = channel.queue_declare(exclusive=True)
queue_name = result.method.queue
binding_keys = ['opensuse.openqa.#', '*.openqa.comment.create']
for binding_key in binding_keys:
	channel.queue_bind(exchange='pubsub', queue=queue_name, routing_key=binding_key)
def callback(ch, method, properties, body):
	topic = method.routing_key
	msg = json.loads(body)
channel.basic_consume(callback, queue=queue_name, no_ack=True)
channel.start_consuming()
```


Topic format
------------

The message topic has the following format:

	SCOPE.APPLICATION.OBJECT.ACTION
	^     ^           ^      ^
	|     |           |      |
	|     |           |      +----- What happend with the object (verb in nonfinite form)
	|     |           +------------ What object was touched by the action
	|     +------------------------ In which application did the event occur
	+------------------------------ Was it an internal or external application

Because of obvious reasons an item of the topic **must not** contain a dot.
For word separation use underscores.

Examples:

- `suse.openqa.comment.create`
- `opensuse.openqa.comment.modify`
- `opensuse.obs.package.branch`
- `opensuse.obs.package.build_fail`
