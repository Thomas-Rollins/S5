import sys
import os
import subprocess

import aws_s3

STRIP_CHARS = '\r\n'


def get_os():
    return os.name

def run_sys_cmd(command):
    return subprocess.Popen(command, shell=True).wait()

def get_cmd(input):
    input = input.rstrip()
    if not len(input):
        return None
    
    command, args = [None, None]
    try:
        command, args = input.split(None, 1)
    except ValueError:
       command = input
    return command, args

def run_cmd(cloud, command, args):
    try:
        func = getattr(cloud, 'do_' + command)
    except AttributeError:
        print('-S5: {}: command not found'.format(command))
        return 1
    return func(args)
    
def S5():
    
    prompt = 'S5> '

    cloud = aws_s3.aws_s3()
    intro = cloud.intro
    print(intro)

    is_valid, msg = cloud.is_valid_credentials()
    print(msg)
    if not is_valid:
        sys.exit(1)

    stop = False

    while not stop:
        #primary cmd loop
        print(prompt, end='')
        sys.stdout.flush()
        input = sys.stdin.readline()
        if len(input):
            input = input.rstrip(STRIP_CHARS)
        else:
            continue

        command, args = get_cmd(input)
        result = 1

        if command == 'quit' or command == 'exit':
            stop = True
        result = run_cmd(cloud, command, args)
        print('result:', result)

    return False

### Main ###

S5()