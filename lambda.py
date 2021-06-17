import os
import boto3
import json

# Define variables and service names
ami = 'ami-0d2fb06f3c1484132' # amazon ami
instance_type = 't2.micro'
key_name = 'ec2key'
subnet_id = 'subnet-bd01cddb'
security_group = 'sg-b64ec3fd'
kms_key_id = '4cf6c9c6-d305-4330-874b-eb5b3aa0608c'
bucket_name = 'gcsecengtest'

# Get current region
session = boto3.session.Session()
region = session.region_name

# Create Boto client connectors
ec2 = boto3.client('ec2', region_name=region)
s3 = boto3.client('s3', region_name=region)
s3_resource = boto3.resource('s3')

# Main function
def lambda_handler(event, context):
    
    # Create instance with S3 read only IAM role
    instance_read = ec2.run_instances(
        ImageId=ami,
        InstanceType=instance_type,
        KeyName=key_name,
        SubnetId=subnet_id,
        SecurityGroupIds=[security_group],
        IamInstanceProfile={ 'Name': 'S3ReadOnly' },
        MaxCount=1,
        MinCount=1,
        InstanceInitiatedShutdownBehavior='terminate'
    )
    
    # Create instance with S3 read write IAM role
    instance_write = ec2.run_instances(
        ImageId=ami,
        InstanceType=instance_type,
        KeyName=key_name,
        SubnetId=subnet_id,
        SecurityGroupIds=[security_group],
        IamInstanceProfile={ 'Name': 'S3ReadWrite' },
        MaxCount=1,
        MinCount=1,
        InstanceInitiatedShutdownBehavior='terminate'
    )
    
    # Create S3 Bucket
    s3.create_bucket(
        Bucket=bucket_name, 
        CreateBucketConfiguration={
            'LocationConstraint': region
        }
    )
    
    # Encrypt S3 bucket with KMS 
    s3.put_bucket_encryption(
        Bucket=bucket_name, 
        ServerSideEncryptionConfiguration={
            'Rules': [
                {
                    'ApplyServerSideEncryptionByDefault': {
                        'SSEAlgorithm': 'aws:kms',
                        'KMSMasterKeyID': kms_key_id
                    }                    
                }
            ]
        }
    )
    
    # Make S3 bucket private
    s3.put_public_access_block(
        Bucket=bucket_name,
        PublicAccessBlockConfiguration={
            'BlockPublicAcls': True,
            'IgnorePublicAcls': True,
            'BlockPublicPolicy': True,
            'RestrictPublicBuckets': True
        },
    )
    
    # Apply S3 bucket policy to further restrict access to IAM roles
    with open('bucket_policy.json') as f:
        bucket_policy = json.load(f)
        s3_resource.BucketPolicy(bucket_name).put(Policy=json.dumps(bucket_policy))

    # Retrieve EC2 Instance IDs and return for user info
    instance_read_id = instance_read['Instances'][0]['InstanceId']
    instance_write_id = instance_write['Instances'][0]['InstanceId']

    return ('ReadOnly: ' + instance_read_id + ' Write: ' + instance_write_id)

