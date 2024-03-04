import os
import tempfile
import tarfile
from minio import Minio, error
from dotenv import load_dotenv

load_dotenv(verbose=True)

client = Minio(
    secure=os.environ["SSL_ON"] == 'True',
    endpoint=os.environ["S3_ENDPOINT"],
    access_key=os.environ["S3_ACCESS_KEY"],
    secret_key=os.environ["S3_SECRET_KEY"],
    region='eu-central-1'
)


def load_image(s3_path):
    s3_bucket = s3_path['s3-bucket']
    s3_object = s3_path['s3-path']

    try:
        response = client.get_object(s3_bucket, s3_object)
    except error.S3Error:
        raise Exception({'type': 'S3', 'message': 'S3 error - mostly likely access was denied.'})

    temp_dir = tempfile.TemporaryDirectory()
    tar_path = temp_dir.name + '/dicom.tar'
    dicom_image_dir_path = temp_dir.name
    os.makedirs(os.path.dirname(dicom_image_dir_path), exist_ok=True)

    with open(tar_path, 'xb') as file_data:
        for d in response.stream(32 * 1024):
            file_data.write(d)

    try:
        response.close()
        response.release_conn()
    except error.S3Error:
        raise Exception({'type': 'S3', 'message': 'S3 error - mostly likely file was not found.'})

    with tarfile.open(tar_path) as tar:
        subdir_and_files = [
            tarinfo for tarinfo in tar.getmembers()
            if not tarinfo.name.startswith("MD5")
        ]
        tar.extractall(path=dicom_image_dir_path, members=subdir_and_files)
        tar.close()

    os.remove(dicom_image_dir_path + '/dicom.tar')
    dicom_image_dir_path += '/' + os.listdir(dicom_image_dir_path)[0]
    return dicom_image_dir_path, temp_dir


def store_file(dir_path, file_path, s3_output_path):
    s3_bucket = s3_output_path['s3-bucket']

    # Check for trailing /
    s3_path = s3_output_path['s3-path']

    result = client.put_object(
        s3_bucket + "/" + s3_path + "/", file_path, dir_path + file_path, length=-1, part_size=10 * 1024 * 1024,
    )
    return result.object_name
