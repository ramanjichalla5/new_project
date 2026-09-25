"""Deploy Module 3 to an EXISTING SSM-managed EC2 host. Creates no AWS resources."""
import argparse
import json
from pathlib import Path
import re
import time

import boto3
from botocore.exceptions import ClientError
import requests


def deploy(args):
    if not re.fullmatch(r'[0-9a-f]{40}', args.commit):
        raise ValueError('--commit must be a full, published 40-character Git commit SHA')
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    ec2, ssm = session.client('ec2'), session.client('ssm')
    instance = ec2.describe_instances(InstanceIds=[args.instance])['Reservations'][0]['Instances'][0]
    if instance['State']['Name'] != 'running':
        raise RuntimeError('Target instance must already be running')
    public_ip = instance.get('PublicIpAddress')
    if not public_ip:
        raise RuntimeError('Target requires an existing public IPv4 address for public verification')
    online = ssm.describe_instance_information(Filters=[{'Key':'InstanceIds','Values':[args.instance]}])['InstanceInformationList']
    if not online or online[0]['PingStatus'] != 'Online':
        raise RuntimeError('Target must be online in AWS Systems Manager; configure its SSM instance role first')
    # Existing Docker and git are prerequisites; do not change the host package manager or unrelated apps.
    # A candidate on loopback is tested before switching the public service container.
    script = f'''#!/bin/bash
set -euo pipefail
command -v docker
command -v git
docker info >/dev/null
release=/opt/zepto/releases/{args.commit}
mkdir -p "$release"
if [ ! -d "$release/.git" ]; then
  git clone https://github.com/ramanjichalla5/new_project.git "$release"
fi
cd "$release"
git fetch origin {args.commit}
git checkout --detach {args.commit}
docker build -f support_assistant/Dockerfile -t zepto-support:{args.commit} .
if docker container inspect zepto-support-candidate >/dev/null 2>&1; then
  echo 'Candidate container already exists; inspect it before retrying.' >&2; exit 1
fi
docker run -d --name zepto-support-candidate -p 127.0.0.1:17860:7860 --memory=3g --cpus=2 zepto-support:{args.commit}
trap 'docker rm -f zepto-support-candidate >/dev/null 2>&1 || true' EXIT
ready=0
for attempt in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:17860/health; then ready=1; break; fi
  sleep 2
done
test "$ready" = 1
curl -fsS -H 'Content-Type: application/json' -d '{{"query":"What is the standard delivery fee?"}}' http://127.0.0.1:17860/ask
docker rm -f zepto-support-candidate
trap - EXIT
backup=zepto-support-backup-$(date +%s)
previous=0
if docker container inspect zepto-support >/dev/null 2>&1; then
  docker stop zepto-support
  docker rename zepto-support "$backup"
  previous=1
fi
rollback() {{
  docker rm -f zepto-support >/dev/null 2>&1 || true
  if [ "$previous" = 1 ]; then docker rename "$backup" zepto-support; docker start zepto-support; fi
}}
trap rollback ERR
docker run -d --restart unless-stopped --name zepto-support -p 7860:7860 --memory=3g --cpus=2 --log-opt max-size=10m --log-opt max-file=3 zepto-support:{args.commit}
ready=0
for attempt in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:7860/health; then ready=1; break; fi
  sleep 2
done
test "$ready" = 1
trap - ERR
'''
    command = ssm.send_command(InstanceIds=[args.instance], DocumentName='AWS-RunShellScript',
        Parameters={'commands':[script], 'executionTimeout':['3600']}, TimeoutSeconds=3600,
        Comment='Deploy Zepto support assistant at reviewed commit')['Command']['CommandId']
    print(f'SSM command: {command}; target {args.instance} in {args.region}', flush=True)
    deadline = time.monotonic()+3700
    while time.monotonic() < deadline:
        time.sleep(10)
        try:
            state = ssm.get_command_invocation(CommandId=command, InstanceId=args.instance)
        except ClientError as error:
            if error.response['Error']['Code'] == 'InvocationDoesNotExist':
                continue
            raise
        if state['Status'] in ('Pending','InProgress','Delayed'):
            print(f'Deployment {state["Status"]}', flush=True)
            continue
        if state['Status'] != 'Success':
            raise RuntimeError(f'SSM failed: {state["Status"]}\n{state.get("StandardErrorContent", "")}')
        break
    else:
        raise TimeoutError(f'Check SSM command {command}; deploy status is unknown')
    base = f'http://{public_ip}:7860'
    health = requests.get(base+'/health', timeout=15)
    health.raise_for_status()
    assert health.json()['documents'] == 8
    policy = requests.post(base+'/ask', json={'query':'What is the standard delivery fee?'}, timeout=30)
    policy.raise_for_status()
    assert policy.json()['sources'][0] == 'doc_01'
    general = requests.post(base+'/ask', json={'query':'What is two plus two?'}, timeout=30)
    general.raise_for_status()
    assert general.json()['sources'] == []
    proof = {'instance':args.instance, 'region':args.region, 'commit':args.commit,
             'host_ip':public_ip, 'url':base, 'health':health.json(),
             'policy_response':policy.json(), 'general_response':general.json()}
    Path('deployment.json').write_text(json.dumps(proof, indent=2), encoding='utf-8')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', default=None)
    parser.add_argument('--region', default='eu-central-1')
    parser.add_argument('--instance', required=True)
    parser.add_argument('--commit', required=True)
    deploy(parser.parse_args())
