import os
from posixpath import split
from botocore.exceptions import BotoCoreError, ClientError     #Error handling
import boto3
import configparser

import S5Shell

class aws_s3(S5Shell.s5shell):

    aws_session = None
    s3_client = None
    s3_resource = None

    intro = 'Welcome to the AWS S3 Storage Shell (S5)'

    def __init__(self):
        self.aws_session = self.create_session(self.load_confg(), None)
        self.s3_client = self.create_S3_client(self.aws_session)
        self.s3_resource = self.create_S3_resource(self.aws_session)

    def load_confg(self):
        config = configparser.ConfigParser()
        config.read('./S5-S3conf')
        access_key_id = config.get('rollins', 'aws_access_key_id')
        access_key_secret = config.get('rollins', 'aws_secret_access_key')
        credentials = [access_key_id, access_key_secret]
        return credentials

    def create_session(self, credentials, region):
        aws_session = boto3.session.Session(aws_access_key_id=credentials[0],
                                        aws_secret_access_key=credentials[1],
                                        region_name=region,
                                        )

        return aws_session

    def is_valid_credentials(self):
        sts = self.aws_session.client('sts')
        try:
            sts.get_caller_identity()
        except ClientError:
            return False, 'You could not be connected to your S3 storage\nPlease review procedures for authenticated your account on AWS S3'
        
        return True, 'You are now connected to your S3 storage'

    def create_S3_resource(self, session):
        s3 = session.resource('s3')
        return s3

    def create_S3_client(self, session):
        s3 = session.client('s3')
        return s3

    def bucket_exists(self, resource, name):
        try: 
            resource.meta.client.head_bucket(Bucket=name)
        except ClientError as err:
            # logging.error(err)
            return [False, int(err.response['Error']['Code'])]
        except BotoCoreError:
            return [False, 'Invalid Params']
        return [True, None]

    # usa-east-1 will return None
    def get_location(client, bucket_name):
        response = client.get_bucket_location(Bucket=bucket_name)
        return response['LocationConstraint']

    def do_lc_copy(self, args):
        print('Local Copy:', args)
        success = False
        err = None
        # print('args:', args)

        if args == None:
            success = False
            err = 'lc_copy takes 2 arguments.'
        else:
            try:
                local_path, bucket_path = args.split(' ', 1)
            except IndexError:
                success = False
                err = 'Invalid arguments.'
            abs_local_path = self.get_abs_local_path(local_path)

            if(abs_local_path == None or not os.path.exists(abs_local_path)):
                success = False
                err = local_path + ' does not exist or is inaccessible.'
            else:
                try:
                    bucket_name, cloud_path = bucket_path.split(":", 1)
                except IndexError:
                    success = False
                if self.bucket_exists(self.s3_resource, bucket_name)[0] :
                    try:
                        print('local file:', abs_local_path, '\nbucket:', bucket_name, '\nCloud Path:', cloud_path)
                        response = self.s3_client.upload_file(abs_local_path, bucket_name, cloud_path)
                        success = True
                    except ClientError as e:
                        err_code = err.response['Code']
                        err = 'Error: ' + err_code
                        success = False
                else:
                    err = 'Bucket ' + bucket_name + ' does not exist'
                    success = False
        if err != None: 
            print('Error:', err)
        return 0 if success else 1
        
    def do_cl_copy(self, args):
        print('Cloud copy:', args)
        success = False

        if args == None:
            success = False
        elif ':' in args:
            try:
                bucket_path = args.split(':', 1)
                result = self.bucket_exists(self.s3_resource, bucket_path[0])
                if result[0]:
                    self.cloud_cur_bucket = bucket_path[0]
                    self.cloud_wDir = bucket_path[1]
                    success = True
            except IndexError:
                success = False

        return 0 if success else 1

    def do_create_bucket(self, args):
        print('create a bucket:', args)
        return False

    def do_create_folder(self, args):
        print('create folder', args)
        return False

    def do_ch_folder(self, args):
        success = False
        if args == None:
            success = False
            # case 1a: <abs path>
        # elif os.path.isabs(args):
        #     self.local_wDir = args
        #     success = True
        #     print(self.local_wDir)
        # # case 1b <relative path>
        # elif os.path.exists(os.path.normpath(os.path.join(self.local_wDir, args))):
        #     self.local_wDir = os.path.normpath(os.path.join(self.local_wDir, args))
        #     success = True
        # case 2: <bucket name>:<path>
        # TODO: verifiiy <path> is valid within S3 Bucket
        elif ':' in args:
            try:
                bucket_path = args.split(':', 1)
                result = self.bucket_exists(self.s3_resource, bucket_path[0])
                if result[0]:
                    self.cloud_cur_bucket = bucket_path[0]
                    self.cloud_wDir = bucket_path[1]
                    success = True
            except IndexError:
                success = False

        elif self.bucket_exists(self.s3_resource, args)[0]:
            self.cloud_cur_bucket = args
            self.cloud_wDir =''
            success = True
        else:
            arg_path = args.split('/')
           
            cloud_path = self.cloud_wDir
            cloud_path = cloud_path.split('/')
            cloud_path.reverse()

            if(len(arg_path) > len(cloud_path) + 1):
               success = False
            else:
                trimmed_path = [x for x in cloud_path if (len(cloud_path) >= len(arg_path) and x != '')]
                print('trimmed path:', trimmed_path)
                if arg_path[0] == '.':
                    try:
                        trimmed_path.insert(0, arg_path[1])
                        success = True
                    except IndexError:
                        pass
                else:
                    try:
                        while arg_path[0] == '..':
                            trimmed_path.pop(0)
                            arg_path.pop(0)
                            success = True
                    except IndexError:
                        pass
                if len(arg_path) > 0:
                    arg_path.reverse()
                    for p in arg_path:
                        print('p:', p)
                        if p == '.':
                            success = False
                            break
                        elif p == '..':
                            success = False
                            break
                        else:
                            trimmed_path.insert(0, p)
                if(success):
                    trimmed_path.reverse()
                    self.cloud_wDir = '/'.join(trimmed_path)
                
      
        if not success:
            print('Invalid arguments. Usages:', os.linesep, 'ch_folder <bucket name>', os.linesep,
                    'ch_folder <bucket name>:<full pathname of directory>', os.linesep,
                    'ch_folder <full or relative pathname of local directory>'
                    )
        print('current bucket:', self.cloud_cur_bucket)
        print('cloud path:', self.cloud_wDir)
        print('local wDir:', self.local_wDir)
        return 0 if success else 1

    def do_cwf(self, args):
        if(self.cloud_wDir == ''):
            print(self.cloud_cur_bucket)
        else :
            print(self.cloud_cur_bucket + ':' + self.cloud_wDir)
        return 0

    def do_list(self, args):
        print('list buckets', args)

    def do_ccopy(self, args):
        print('copy from s3 loc to s3 loc')

    def do_cdelete(self, args):
        print('delete s3 object', args)
        
    def do_delete_bucket(self, args):
        print('delete bucket', args)
