#!/usr/bin/env bash
python3 - <<'PY'
from confluent_kafka.admin import AdminClient, NewTopic
admin = AdminClient({'bootstrap.servers':'localhost:9092'})
topics = [NewTopic(t, num_partitions=6, replication_factor=1) for t in ['incoming.messages','outgoing.messages','delivery.events','file.uploads','audit.events']]
fs = admin.create_topics(topics)
for t, f in fs.items():
    try:
        f.result()
        print('Created', t)
    except Exception as e:
        print('Error', t, e)
PY
