import sys
import os
import subprocess
import logging
import configparser
from botocore.exceptions import ClientError     #Error handling
import boto3
import cmd


def get_os():
    return os.name

def load_confg():
    config = configparser.ConfigParser()
    config.read('./S5-S3conf')
    access_key_id = config.get('rollins', 'aws_access_key_id')
    access_key_secret = config.get('rollins', 'aws_secret_access_key')
    credentials = [access_key_id, access_key_secret]
    return credentials

def create_aws_session(credentials, region):
    aws_session = boto3.session.Session(aws_access_key_id=credentials[0],
                                    aws_secret_access_key=credentials[1],
                                    region_name=region,
                                    )

    sts = aws_session.client('sts')
    try:
        sts.get_caller_identity()
    except ClientError:
        print('You could not be connected to your S3 storage\nPlease review procedures for authenticated your account on AWS S3')
        return None
    return aws_session
    

def create_aws_S3_resource(session):
    s3 = session.resource('s3')
    return s3

def create_aws_S3_client(session):
    s3 = session.client('s3')
    return s3

def bucket_exists(resource, name):
    print(name)
    try: 
        resource.meta.client.head_bucket(Bucket=name)
    except ClientError as err:
        # logging.error(err)
        return [False, int(err.response['Error']['Code'])]
    return [True, None]

# usa-east-1 will return None
def get_location(client, bucket_name):
    response = client.get_bucket_location(Bucket=bucket_name)
    return response['LocationConstraint']

### End of Functions


def run_sys_cmd(command):
    return subprocess.Popen(command, shell=True).wait()
    


class S5Shell(cmd.Cmd):
    prompt = 'S5> '
    intro = 'Welcome to the AWS S3 Storage Shell (S5)'
    aws_session = None

    aws_session = create_aws_session(load_confg(), None)
    if aws_session == None:
        sys.exit()
    else:
        print('You are now connected to your S3 storage')
    
    local_wDir = os.getcwd()
    cloud_cur_bucket = ''
    cloud_wDir = '/'

    s3_client = create_aws_S3_client(aws_session)
    s3_resource = create_aws_S3_resource(aws_session) 

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.aliases = {'q'     : self.do_exit,
                        'quit'  : self.do_exit
                        }

    def default(self, args):
        cmd, arg, args = self.parseline(args)
        if cmd in self.aliases:
            self.aliases[cmd](arg)
            return True
        else:
            if run_sys_cmd(args):
                print('invalid cmd')
                return False

    def do_exit(self, args):
        '''exit the S5 Shell'''
        print("Goodbye")
        return False

    def do_lc_copy(self, args):
        print('Local Copy:', args)
        return False
    
    def do_cl_copy(self, args):
        print('Cloud copy:', args)
        return False

    def do_create_bucket(self, args):
        print('create a bucket:', args)
        return False

    def do_create_folder(self, args):
        print('create folder', args)
        return False

    def do_ch_folder(self, args):
        success = False
        print('change folder:', args)
        # case 1a: <abs path>
        if os.path.isabs(args):
            self.local_wDir = args
            success = True
            print(self.local_wDir)
        # case 1b <relative path>
        elif os.path.exists(os.path.abspath(args)):
            self.local_wDir = os.path.abspath(args)
            success = True
        # case 2: <bucket name>:<path>
        # TODO: verifiiy <path> is valid within S3 Bucket
        elif ':' in args:
            try:
                bucket_path = args.split(':', 1)
                result = bucket_exists(self.s3_resource, bucket_path[0])

                if result[0]:
                    self.cloud_cur_bucket = bucket_path[0]
                    self.cloud_wDir = bucket_path[1]
                    success = True
                else:
                    success = False
            except IndexError:
                success = False

            print('current bucket:', self.cloud_cur_bucket)
            print('cloud path:', self.cloud_wDir)

        else: #case 3: <bucket name>
            result = bucket_exists(self.s3_resource, args)
            if result[0] == True:
                print('bucket exists')
                self.cloud_cur_bucket = args
                self.cloud_wDir =''
            else:
                print('')
        if not success:
            print('Invalid arguments. Usages:', os.linesep, 'ch_folder <bucket name>', os.linesep,
                        'ch_folder <bucket name>:<full pathname of directory>', os.linesep,
                        'ch_folder <full or relative pathname of local directory>'
                        )

    def do_cwf(self, args):
        print('change working folder', args)

    def do_list(self, args):
        print('list buckets', args)

    def do_ccopy(self, args):
        print('copy from s3 loc to s3 loc')

    def do_cdelete(self, args):
        print('delete s3 object', args)
    
    def do_delete_bucket(self, args):
        print('delete bucket', args)

### End of S5Shell class
    

    

    
try:
    S5Shell().cmdloop()
except KeyboardInterrupt:
    sys.exit()

# s3_client = create_aws_S3_client(aws_session)
# s3_resource = create_aws_S3_resource(aws_session)

# print(get_location(s3_client, 'cis4010-rollins'))
# print(bucket_exists(s3_resource, 'cis4010-rollins'))
# print(bucket_exists(s3_resource, 'rollins'))