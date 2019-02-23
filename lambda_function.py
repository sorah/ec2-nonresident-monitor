import boto3
import urllib
import json
import os
import datetime

# FIXME: need to use environment variable (it was not supported when I wrote this script yet.)
SLACK_WEBHOOK_URLS = [
]
AWS_REGION = os.environ.get('AWS_REGION', 'ap-northeast-1')

ec2 = boto3.client('ec2', AWS_REGION)

def notify_to_slack(message):
    payload = {
        'attachments': [{
            'text': message,
            'fallback': message,
            'color': 'danger',
            'mrkdwn_in': ['text'],
        }],
    }
    for url in SLACK_WEBHOOK_URLS:
        urllib.request.urlopen(url, json.dumps(payload).encode(encoding='UTF-8'))

def find_nonresident_instances():
    now = datetime.datetime.now().replace(tzinfo=None)
    pager = ec2.get_paginator('describe_instances').paginate(
            Filters=[
                {
                    'Name': 'instance-state-name',
                    'Values': ['running'],
                },
            ],
    )
    nonresident_instances = []
    for reservation in pager.search('Reservations'):
        for instance in reservation['Instances']:
            resident_tag = next((tag for tag in instance.get('Tags', []) if tag['Key'] == 'Resident'), None)
            term = 86400

            if resident_tag == None:
                term = 86400
            elif resident_tag['Value'] == 'permanent':
                continue
            else:
                try:
                    term = int(resident_tag['Value'])
                except ValueError:
                    print('{0} Resident tag is invalid'.format(instance['InstanceId']))

            if (now-instance['LaunchTime'].replace(tzinfo=None)).total_seconds() > term:
                nonresident_instances.append(instance)
    return nonresident_instances

def lambda_handler(event, context):
    nonresident_instances = find_nonresident_instances()
    if len(nonresident_instances) == 0:
        return

    text_lines = [':3fear: *Long running nonresident instances found!*', '']
    for instance in nonresident_instances:
        name = '?'
        name_tag = next((tag for tag in instance.get('Tags', []) if tag['Key'] == 'Name'), None)
        if name_tag == None:
            name = instance['InstanceId']
        else:
            name = name_tag['Value']

        line = '{2}: `{0}` {1}'.format(name, instance['InstanceType'], instance['LaunchTime'].isoformat())
        text_lines.append(line)

    print("\n".join(text_lines))

    notify_to_slack("\n".join(text_lines))


if __name__ == '__main__':
    lambda_handler({}, None)
