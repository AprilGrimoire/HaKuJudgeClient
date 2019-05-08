#!/usr/bin/env python3

import os
import time
import json
import base64
import requests
import logging
from bs4 import BeautifulSoup

import config
import judge

def handle(submission):
    global session
    logging.info('Judging submission {}'.format(submission['id']))
    logging.debug(submission)
    problem_dir = 'testdata/{}'.format(submission['problem_id'])
    os.system('mkdir -p {}'.format(problem_dir))
    os.system('touch {}/digest'.format(problem_dir))
    with open('{}/digest'.format(problem_dir), 'r') as f:
        digest_local = f.read()
    resp = session.get(config.address + '/problems/{}/digest'.format(submission['problem_id']))
    digest_server = json.loads(resp.text)['digest']
    if digest_local != digest_server:
        logging.info('Updating testdata for problem {}'.format(submission['problem_id']))
        resp = session.get(config.address + '/problems/{}/fetch'.format(submission['problem_id']))
        testdata = json.loads(resp.text)['testdata']
        testdata = base64.b64decode(testdata)
        with open('{}/problem.zip'.format(problem_dir), 'wb') as f:
            f.write(testdata)
        os.system('unzip {0}/problem.zip -d {0}'.format(problem_dir))
        with open('{}/digest'.format(problem_dir), 'w') as f:
            f.write(digest_server)

    os.system('mkdir -p temp')
    with open('temp/target.cpp', 'w') as f:
        f.write(submission['source'])
    result = judge.judge('{}/problem/problem.json'.format(problem_dir), 'temp/target.cpp')
    logging.info('Judge complete')
    logging.debug(result)
    resp = session.get(config.address + '/submissions/{}/edit'.format(submission['id']))
    soup = BeautifulSoup(resp.text, features="lxml")
    token = soup.find('input', attrs={'name': '_token'})['value']
    payload = {'_token': token, 'status': result['status'], 'score': result['score'], 'detail': json.dumps(result['detail'])}
    if result['time']:
        payload['time'] = round(result['time'] * 1000)
    if result['memory']:
        payload['memory'] = round(result['memory'] * 1024)
    print(payload)
    resp = session.patch(config.address + '/submissions/{}'.format(submission['id']),
                         data=payload)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    session = requests.Session()
    for key, value in config.cookies.items():
        session.cookies[key] = value
    while True:
        resp = session.get(config.address + '/attach_submission')
        resp = json.loads(resp.text)
        if resp['success']:
            handle(resp['submission'])
        else:
            time.sleep(config.CHECK_INTERVAL)
