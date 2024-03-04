import os
import json
import sys

import segmentor
from datetime import datetime

from dotenv import load_dotenv
from kafka.errors import CommitFailedError
from kafka.consumer import KafkaConsumer
from kafka.producer import KafkaProducer

load_dotenv(verbose=True)


def get_modus_props():
    modus = os.environ['MODUS']
    bootstrap_server = os.environ['BOOTSTRAP_SERVER'].split(',')
    max_poll = int(os.environ['MAX_POLL_RECORDS'])

    match modus:
        case 'index':
            in_topic = os.environ['INCOMING_INDEX_TOPIC_NAME']
            out_topic = os.environ['OUTGOING_INDEX_TOPIC_NAME']
            consumer_group = os.environ['INDEX_CONSUMER_GROUP']
            export_format = os.environ['INDEX_EXPORT']
        case 'segmentation':
            in_topic = os.environ['INCOMING_SEGMENTATION_TOPIC_NAME']
            out_topic = os.environ['OUTGOING_SEGMENTATION_TOPIC_NAME']
            consumer_group = os.environ['SEGMENTATION_CONSUMER_GROUP']
            export_format = os.environ['SEGMENTATION_EXPORT']
        case _:
            raise IOError

    return modus, bootstrap_server, max_poll, in_topic, out_topic, consumer_group, export_format


def get_model_provenance():
    libraries = ['torch', 'totalsegmentator', 'nnunet-customized']
    provenance = {}
    with open("environment.yml") as dep_file:
        deps = dep_file.read()
        splits = deps.split('\n')
        # Start after the channels section
        for s in splits[5:]:
            for lib in libraries:
                if lib in s:
                    provenance[lib] = s.split('==')[1]
    return provenance


def send_error(message, error):
    _, bootstrap_server, _, _, _, _ = get_modus_props()
    producer = KafkaProducer(value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                             bootstrap_servers=bootstrap_server)

    res = dict()
    res['dateCreated'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    res['message'] = message[6]
    res['error'] = str(error)

    producer.send(topic=os.environ['ERROR_TOPIC_NAME'], value=res)
    producer.flush()


def start_consumer():
    modus, bootstrap_server, max_poll, in_topic, out_topic, consumer_group, export_format = get_modus_props()
    print("Start CT-Indexer in mode: " + str(modus))

    try:
        provenance = get_model_provenance()
        consumer = KafkaConsumer(
            bootstrap_servers=bootstrap_server,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            group_id=consumer_group,
            max_poll_records=max_poll,
            value_deserializer=lambda x: json.loads(x.decode("utf-8"))
        )

    except Exception as error:
        print('ERROR ' + str(error.__module__) + ': ' + str(error), file=sys.stderr)
        exit()

    consumer.subscribe([in_topic])
    for message in consumer:
        try:
            consumer.commit()
            payload = message[6]
            identification = payload['identification']
            s3_input = payload['s3-input']

            match modus:
                case 'index':
                    res, stats = segmentor.index_ct(s3_input=s3_input)
                case 'segmentation':
                    s3_output = payload['s3-output']
                    res = segmentor.segment_ct(s3_input=s3_input, s3_output=s3_output)
            res['identification'] = identification
            res['s3-input'] = s3_input
            res['provenance'] = provenance
            res['duration'] = stats
            res['dateCreated'] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

            if export_format == 'fhir':
                print()

            # https://forum.confluent.io/t/what-should-i-use-as-the-key-for-my-kafka-message/312
            producer = KafkaProducer(value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                                     bootstrap_servers=bootstrap_server)
            producer.send(topic=out_topic, value=res)
            producer.flush()

        except Exception as error:
            print('Indexing failed for: ' + str(s3_input))
            print('ERROR ' + str(error), file=sys.stderr)
            send_error(message, error)


if __name__ == "__main__":
    start_consumer()
