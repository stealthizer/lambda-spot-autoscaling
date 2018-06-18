#!/usr/bin/env python3

import boto3
import json
import time
import datetime
import argparse


def check_if_instance_exists(instanceId):
    try:
        response = ec2Client.describe_instances(InstanceIds=[instanceId])
    except:
        return False
        exit(1)
    else:
        return True

def expires():
    return int(time.time()+ 120)

def future_date(future):
    return future.strftime("%b %d, %Y %H:%M:%S")

def put_cloudwatch_event():
    return cloudwatch_events.put_events(
        Entries=[
            {
                'Source': 'mARC_demo',
                'DetailType': 'EC2 Spot Instance Interruption Warning',
                'Detail': json.dumps({
                    'instance-id': instanceId,
                    'instance-action': 'terminate'
                })
            }
        ]
    )

def put_termination_timestamp():
    return "lol"

def remove_termination_timestamp():
    return "lol"



if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Get information from vpc resources')
    parser.add_argument('-i', '--instance', required=True, help='Spot Instance Id to simulate a termination')
    parser.add_argument('-p', '--profile', required=True, help='AWS Profile')
    args = parser.parse_args()

    instanceId = args.instance
    profile_name = args.profile
    region = 'eu-west-1'

    session = boto3.Session(profile_name=profile_name)
    cloudwatch_events = session.client('events', region_name=region)
    ec2Client = session.client('ec2', region_name=region)

    if check_if_instance_exists(instanceId) is True:
        future = datetime.datetime.now() + datetime.timedelta(seconds=2*60)
        response = put_cloudwatch_event()

        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print('Event Created...' + '\n' + str(response))

        dynamodb = session.resource('dynamodb', region_name=region)
        table = dynamodb.Table('terminateDB')
        response = table.put_item(
            Item={
                'termination': future_date(future),
                'ttl': expires(),
            }
        )

        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            print('Set Termination Timestamp for Spot Instances...' + '\n' + str(response))

        print("Counting down to terminate spot instances...")

        now = datetime.datetime.now()
        while (future > now):
            now = datetime.datetime.now()
            print(future - now)
            time.sleep(5)

        print("Terminating instance " + instanceId + "...")
        result = ec2Client.terminate_instances(InstanceIds=[instanceId])
        print(result)

        print(remove_termination_timestamp())

    else:
        print("There is no such instance")
