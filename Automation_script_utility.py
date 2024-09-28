import boto3
import time
import uuid

# Initialize a session using default credential and configuration settings
session = boto3.Session(region_name='us-east-2')

# Create service clients
ec2 = session.client('ec2')
s3_resource = session.resource('s3')  
s3_client = session.client('s3')     
sqs = session.client('sqs')

def create_ec2_instance():
    try:
        response = ec2.run_instances(
            ImageId='ami-0c55b159cbfafe1f0',  
            InstanceType='t2.micro',
            MinCount=1,
            MaxCount=1,
            KeyName='asu_kp'
        )
        instance_id = response['Instances'][0]['InstanceId']
        print(f"EC2 Instance created with ID: {instance_id}")
        return instance_id
    except Exception as e:
        print(f"Failed to create EC2 instance: {e}")

def create_bucket():
    bucket_name = f"hpandit-{uuid.uuid4()}"
    try:
        s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={
            'LocationConstraint': session.region_name})
        print(f"Bucket created with name: {bucket_name}")
        return bucket_name
    except Exception as e:
        print(f"Failed to create bucket: {e}")

def create_sqs_queue():
    queue_name = "hrushipandit_queue.fifo"
    try:
        response = sqs.create_queue(
            QueueName=queue_name,
            Attributes={
                'FifoQueue': 'true',
                'ContentBasedDeduplication': 'true'
            }
        )
        queue_url = response['QueueUrl']
        print(f"SQS Queue created with URL: {queue_url}")
        return queue_url
    except Exception as e:
        print(f"Failed to create SQS queue: {e}")

def list_ec2_instances():
    try:
        instances = ec2.describe_instances()
        print("Listing EC2 Instances:")
        for reservation in instances['Reservations']:
            for instance in reservation['Instances']:
                print(f"Instance ID: {instance['InstanceId']}, State: {instance['State']['Name']}")
    except Exception as e:
        print(f"Failed to list EC2 instances: {e}")

def list_s3_buckets():
    try:
        buckets = s3_client.list_buckets()
        print("Listing S3 Buckets:")
        for bucket in buckets['Buckets']:
            print(f"Bucket Name: {bucket['Name']}")
    except Exception as e:
        print(f"Failed to list S3 buckets: {e}")

def list_sqs_queues():
    try:
        queues = sqs.list_queues()
        print("Listing SQS Queues:")
        if 'QueueUrls' in queues:
            for url in queues['QueueUrls']:
                print(f"Queue URL: {url}")
    except Exception as e:
        print(f"Failed to list SQS queues: {e}")

def upload_file_to_s3(bucket_name, file_name, content):
    try:
        s3_client.put_object(Bucket=bucket_name, Key=file_name, Body=content)
        print(f"File {file_name} uploaded to bucket {bucket_name}")
    except Exception as e:
        print(f"Failed to upload file to S3: {e}")

def send_sqs_message(queue_url, message_body, message_name):
    try:
        response = sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=message_body,
            MessageGroupId='messageGroup1',
            MessageAttributes={
                'MessageName': {
                    'DataType': 'String',
                    'StringValue': message_name
                }
            }
        )
        print(f"Message sent to SQS: {response['MessageId']} with name '{message_name}'")
    except Exception as e:
        print(f"Failed to send message to SQS: {e}")

def receive_sqs_message(queue_url):
    # Fetch the message along with its attributes
    messages = sqs.receive_message(
        QueueUrl=queue_url,
        MaxNumberOfMessages=1,
        MessageAttributeNames=['All']  
    )
    if 'Messages' in messages:
        for message in messages['Messages']:
            message_body = message['Body']
            # Extract message attributes, specifically the 'MessageName'
            message_name = message['MessageAttributes']['MessageName']['StringValue'] if 'MessageName' in message['MessageAttributes'] else "No name provided"
            print("Received message name:", message_name)
            print("Received message body:", message_body)
            # Delete the message from the queue to prevent it from being read again
            sqs.delete_message(QueueUrl=queue_url, ReceiptHandle=message['ReceiptHandle'])

def count_messages_in_queue(queue_url):
    # Function to count messages in the queue
    response = sqs.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['ApproximateNumberOfMessages']
    )
    message_count = response['Attributes']['ApproximateNumberOfMessages']
    print("Number of messages in the queue:\n", message_count)
    return int(message_count)

def delete_ec2_instance(instance_id):
    try:
        ec2.terminate_instances(InstanceIds=[instance_id])
        print(f"EC2 Instance {instance_id} is terminating...")
    except Exception as e:
        print(f"Failed to terminate EC2 instance {instance_id}: {e}")

def delete_bucket(bucket_name):
    try:
        # First, empty the bucket using the resource interface
        bucket = s3_resource.Bucket(bucket_name)
        bucket.objects.all().delete()  # Delete all objects in the bucket
        # Then, delete the bucket using the client interface
        s3_client.delete_bucket(Bucket=bucket_name)
        print(f"S3 Bucket {bucket_name} deleted successfully.")
    except Exception as e:
        print(f"Failed to delete S3 bucket {bucket_name}: {e}")

def delete_sqs_queue(queue_url):
    try:
        sqs.delete_queue(QueueUrl=queue_url)
        print(f"SQS Queue {queue_url} deleted successfully.")
    except Exception as e:
        print(f"Failed to delete SQS queue {queue_url}: {e}")

# Main cleanup function
def cleanup_resources(instance_id, bucket_name, queue_url):
    delete_ec2_instance(instance_id)
    delete_bucket(bucket_name)
    delete_sqs_queue(queue_url)
    
def wait_for_queue_deletion(queue_url):
    """ Polls SQS to confirm queue is deleted """
    print("Waiting for queue to be fully deleted...")
    for _ in range(10):  # Retry up to 10 times
        try:
            queues = sqs.list_queues()
            if 'QueueUrls' not in queues or queue_url not in queues['QueueUrls']:
                print("Queue deletion confirmed.")
                return
        except Exception as e:
            print(f"Error checking queues: {e}")
        time.sleep(3)  # Wait for 3 seconds before retrying
    print("Queue still listed after deletion attempts.")

# Initialize a session using your credentials
session = boto3.Session(
    aws_access_key_id='YOUR_AWS_ACCESS_KEY_ID',
    aws_secret_access_key='YOUR_AWS_SECRET_ACCESS_KEY',
    region_name='us-east-2' 
)
# Create service clients
ec2 = session.client('ec2')
s3_resource = session.resource('s3')  # Use resource for S3 bucket manipulation
s3_client = session.client('s3')      # Use client for bucket deletion
sqs = session.client('sqs')

instance_id = create_ec2_instance()
bucket_name = create_bucket()
queue_url = create_sqs_queue()

time.sleep(60)
print("Request sent, wait for 1 min\n")

# List all resources after the wait
list_ec2_instances()
list_s3_buckets()
list_sqs_queues()

# Upload a file and send/receive a message
upload_file_to_s3(bucket_name, "CSE546test.txt", "")
send_sqs_message(queue_url, "This is a test message","test message")

initial_message_count = count_messages_in_queue(queue_url) 
receive_sqs_message(queue_url)
final_message_count = count_messages_in_queue(queue_url)

time.sleep(10)
print("Waiting for 10 seconds before resource cleanup...\n")

# Clean up resources
cleanup_resources(instance_id, bucket_name, queue_url)
wait_for_queue_deletion(queue_url)

time.sleep(40)
print("Resources deleted, Waiting for 20 seconds before listing out...\n")

list_ec2_instances()
list_s3_buckets()
list_sqs_queues()
