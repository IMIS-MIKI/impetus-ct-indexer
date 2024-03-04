import os
import io
from datetime import datetime

from contextlib import redirect_stdout
from totalsegmentator.python_api import totalsegmentator
import json

import s3_connector
import snomed_ct_mapping
import radlex_mapping
import tempfile


def index_ct(s3_input):
    print('Loading: \t' + str(s3_input))
    start = datetime.now()
    image_path, temp_dir = s3_connector.load_image(s3_input)
    loading_time = datetime.now()
    check_valid_input(image_path)

    res = dict()
    print('Indexing: \t' + str(s3_input))
    with tempfile.TemporaryDirectory() as tmp_dir:
        trap = io.StringIO()
        try:
            with redirect_stdout(trap):
                totalsegmentator(image_path, tmp_dir, statistics=True, preview=True, fast=True, body_seg=True, force_split=True, skip_saving=True)
        except Exception:
            raise Exception({'type': 'TotalSegmentator', 'message': 'failed - logs: \n' + str(trap.getvalue()) + '\n'})

        f = open(tmp_dir + "/statistics.json")
        data = json.load(f)
        for i in data:
            if data[i]['volume'] > 0:
                res[i] = data[i]
                res[i]['coding'] = [snomed_ct_mapping.mapping[i]['code'], radlex_mapping.mapping[i]['code']]
        f.close()
        temp = dict()
        temp['labels'] = res
        end = datetime.now()
        stats = dict()
        stats['total'] = str(end - start)
        stats['loading'] = str(loading_time - start)
        stats['indexing'] = str(end - loading_time)
        print('Duration: \t' + str(stats))
        print('Complete: \t' + str(s3_input))
        print()
    return temp, stats


def segment_ct(s3_input, s3_output):
    print('Loading: ' + str(s3_input))
    image_path, temp_dir = s3_connector.load_image(s3_input)
    check_valid_input(image_path)

    res = set()
    print('Segmenting: ' + str(s3_input))
    with tempfile.TemporaryDirectory() as tmp_dir:
        totalsegmentator(statistics=True, fast=True, body_seg=True, force_split=True)
        for file in os.listdir(tmp_dir):
            res.add(s3_connector.store_file(tmp_dir, file, s3_output))
    temp_dir.cleanup()
    return res


def check_valid_input(image_path):
    if len(os.listdir(image_path)) < int(os.environ["MIN_FILES_NUMBER"]):
        raise Exception({'type': 'Validation', 'message': 'Input Validation failed: < 10 images.'}
                        )
