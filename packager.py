import os
import zipfile
import hashlib
import json
import boto3
import logging
import argparse
import sys
from logging.handlers import RotatingFileHandler
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()
# handler = logging.StreamHandler()
handler = RotatingFileHandler("packager.log", maxBytes=20971520, backupCount=5)
formatter = logging.Formatter('%(levelname)-8s %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def zipdir(path, ziph):
    # ziph is zipfile handle
    for root, dirs, files in os.walk(path):
        for file in files:
            ziph.write(os.path.join(root, file))

def create_zip_files(dirs):
    for dir in dirs:
        zipf = zipfile.ZipFile(dir+'.zip', 'w', zipfile.ZIP_DEFLATED)
        zipdir(dir+'/', zipf)
    zipf.close()

def get_digest(files):
    h = hashlib.sha256()
    hashes= []
    for file in files:
        file_path = file
        with open(file_path, 'rb') as f:
            bytes = f.read()  # read entire file as bytes
            readable_hash = hashlib.sha256(bytes).hexdigest();
            hashes.append({file_path :readable_hash})
    return hashes

def generate_manifest(installer_list, hashes):
    manifest_dict = {}
    try:
        manifest_dict.update(
        {"schemaVersion": "2.0",
         "version": "3.0"})
        os_packages_dict ={}
        for installer in installer_list:
            os_packages_dict.update(
                {
                    installer['os']:
                     {"_any":
                          {"x86_64":
                                   {"file": installer['file']}
                           }
                      }
                })
        manifest_dict["packages"] = os_packages_dict
        obj = {}
        for hash in hashes:
            for k,v in hash.items():
                obj.update({k:{'checksums':{"sha256": v}}})
        print(obj)
        files = {"files":obj}
        manifest_dict.update(files)
    except Exception as e:
        print ('Exception {}'.format(e))

    with open('manifest.json', 'w') as file:
        file.write(json.dumps(manifest_dict))

def create_bucket(bucket_name, region):
    """Create an S3 bucket in a specified region

    If a region is not specified, the bucket is created in the S3 default
    region (us-east-1).

    :param bucket_name: Bucket to create
    :param region: String region to create bucket in, e.g., 'us-west-2'
    :return: True if bucket created, else False
    """

    print('Creating bucket:')
    try:
        s3_client = boto3.client('s3', region_name=region)
        location = {'LocationConstraint': region}
        s3_client.create_bucket(Bucket=bucket_name,CreateBucketConfiguration=location)
    except ClientError as e:
        print('Error creating bucket {}'.format(ClientError))
        return False
    return True

def bucket_exists(bucket_name,region):
    s3_client = boto3.client('s3',region_name=region)
    response = s3_client.list_buckets()

    # Output True if bucket exists
    print('Bucket already exists:')
    for bucket in response['Buckets']:
        if bucket_name ==  bucket["Name"]:
            return True
    return False

def createDocument(region, filepath, package_name):
    # aws ssm create-document --name "Falcon-ohio" --content file://manifest.json --attachments \
    # Key="SourceUrl", Values = "https://falcon-ssm-ohio.s3.us-east-2.amazonaws.com/falcon" \
    # --version-name 1.0.1 \
    # --document-type Package

    try:
        ssm_client = boto3.client('ssm', region_name=region)
        with open(filepath) as openFile:
            documentContent = openFile.read()
            createDocRequest = ssm_client.create_document(
                Content = documentContent,
                Attachments=[
                    {
                        'Key': 'SourceUrl',
                        'Values': [
                            'https://falcon-ssm-ohio.s3.us-east-2.amazonaws.com/falcon',
                        ]
                    },
                ],
                Name=package_name,
                DocumentType='Package',
                DocumentFormat='JSON'
            )
            print('Created ssm package {}:'.format(package_name))
    except Exception as e:
        print('Error creating document {}'.format(e))

def upload_file(file_name, bucket, object_name=None):
    """Upload a file to an S3 bucket

    :param file_name: File to upload
    :param bucket: Bucket to upload to
    :param object_name: S3 object name. If not specified then file_name is used
    :return: True if file was uploaded, else False
    """
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3', region)
    try:
        print('Uploaing file {}:'.format(file_name))
        s3_client.upload_file(file_name, bucket, object_name)
    except ClientError as e:
        print('Upload error {}'.format(e))
        return False
    return True

def get_agent_list(filename):
    try:
        with open(filename, 'rb') as fh:
            json_data=json.loads(fh.read())
        return json_data
    except IOError as error:
        print('Error {} opening file'.format(IOError))
        sys.exit(1)


def main():
    dirs = []
    files = []

    installer_list = get_agent_list(FILENAME)
    dir_list = os.listdir()

    for installer in installer_list:
        dirs.append(installer['dir'])
        files.append(installer['file'])

    folders_exist = all(item in dir_list for item in dirs)

    if not folders_exist:
        print('Check agent list file - Required directories do not exist')
        sys.exit(1)



    create_zip_files(dirs)
    hashes_list = get_digest(files)
    generate_manifest(installer_list, hashes_list)

    if not bucket_exists(s3bucket,region):
        create_bucket(s3bucket, region)

    for file in files:
        s3name = '/falcon/'+file
        upload_file(file, s3bucket, s3name)
    createDocument(region, "manifest.json", package_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get Params to create CRWD SSM Package')
    parser.add_argument('-r', '--aws_region', help='AWS Region', required=True)
    parser.add_argument('-p', '--package_name', help='Package Name', required=True)
    parser.add_argument('-b', '--s3bucket', help='Package Name', required=True)

    args = parser.parse_args()

    region = args.aws_region
    package_name = args.package_name
    s3bucket = args.s3bucket
    FILENAME = 'agent_list.json'

    main()




