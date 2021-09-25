import os
from posixpath import split
from typing import Any
from botocore.exceptions import BotoCoreError, ClientError     #Error handling
import boto3
import configparser

import S5Shell

class aws_s3(S5Shell.s5shell):

    aws_session = None
    s3_client = None
    s3_resource = None

    intro = 'Welcome to the AWS S3 Storage Shell (S5)'

    def __init__(self) -> None:
        self.aws_session = self.__create_session__(self.load_confg(), None)
        self.s3_client = self.__create_S3_client__(self.aws_session)
        self.s3_resource = self.__create_S3_resource__(self.aws_session)

    def load_confg(self) -> list:
        config = configparser.ConfigParser()
        config.read('./S5-S3conf')
        access_key_id = config.get('rollins', 'aws_access_key_id')
        access_key_secret = config.get('rollins', 'aws_secret_access_key')
        credentials = [access_key_id, access_key_secret]
        return credentials

    def __create_session__(self, credentials, region):
        aws_session = boto3.session.Session(aws_access_key_id=credentials[0],
                                        aws_secret_access_key=credentials[1],
                                        region_name=region,
                                        )

        return aws_session

    def is_valid_credentials(self) -> tuple[bool, str]:
        sts = self.aws_session.client('sts')
        try:
            sts.get_caller_identity()
        except ClientError:
            return False, 'You could not be connected to your S3 storage\nPlease review procedures for authenticating your account on AWS S3'
        
        return True, 'You are now connected to your S3 storage'

    def __create_S3_resource__(self, session) -> object:
        s3 = session.resource('s3')
        return s3

    def __create_S3_client__(self, session) -> object:
        s3 = session.client('s3')
        return s3

    def __bucket_exists__(self, resource, name) ->list[bool, Any]:
        try: 
            resource.meta.client.head_bucket(Bucket=name)
        except ClientError as err:
            # logging.error(err)
            return [False, int(err.response['Error']['Code'])]
        except BotoCoreError:
            return [False, 'Invalid Params']
        return [True, None]

    def __object_exists__(self, client, object_path):
        try:
            self.s3_client.head_object(Bucket=self.cloud_cur_bucket, Key=object_path)
            return True
        except ClientError as e:
            return False
        
    # usa-east-1 will return None
    def get_location(client, bucket_name) -> str:
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
                if self.__bucket_exists__(self.s3_resource, bucket_name)[0] :
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
                result = self.__bucket_exists__(self.s3_resource, bucket_path[0])
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

    # evaluate if folder exists using s3.Object('bucket', 'object name').load()
    # if at root and there is no : then it must be a bucket
    # ch_folder bucket_name: goes directly to a new bucket?

    def do_ch_folder(self, args):
        if isinstance(args, list):
            args[:] = [x for x in args if x.strip()]
        success = False
        err_msg= ''
        if args == None  or  ' ' in args:
            err_msg = 'Invalid Arguments' + os.linesep
            success = False
        
        #go back to top-level
        elif args == '/':
           self.cloud_cur_bucket = '/'
           self.cloud_wDir = ''
           success = True

        elif ':' in args:
            try:
                bucket_path = args.split(':', 1)
                result = self.__bucket_exists__(self.s3_resource, bucket_path[0])
                if result[0]:
                    self.cloud_wDir = ''
                    success = True
                    if bucket_path[1] != '':
                        try:
                            self.s3_client.head_object(Bucket=bucket_path[0], Key=bucket_path[1])
                            self.cloud_wDir = bucket_path[1]
                            success = True
                        except ClientError as e:
                            err_msg = ('The object at ' + bucket_path[0] + ':' + bucket_path[1] 
                                    + ' does not exist or is inaccessible' + os.linesep)
                            success = False
                    if success:
                        self.cloud_cur_bucket = bucket_path[0]
            except IndexError:
                success = False
        #relative path - change to a resolve_relative_path() function
        elif self.cloud_cur_bucket != '/':
            arg_path = args.split('/')
            print(arg_path)
            arg_path[:] = [x for x in arg_path if x.strip()]
            print(arg_path)
            cloud_dir = self.cloud_wDir
            cloud_path = cloud_dir.split('/')
            cloud_path[:] = [x for x in cloud_path if x.strip()]
            print('cloud-path:', cloud_path)
           
            if arg_path[0] == '.':
                arg_path.pop(0)
                print('arg_path1:', arg_path)
                if len(arg_path) == 0:
                    success = True
                else:
                    arg_path_str = '/'.join(arg_path)
                    print('arg_path_str:', arg_path_str)
                    cloud_path.insert(len(cloud_path), arg_path_str)
                
            elif arg_path[0] == '..':
                while arg_path[0] == '..':
                    if len(cloud_path) == 0:
                        err_msg = 'Invalid Arguments: cannot go beyond the top-layer of the bucket.'
                        success = False
                        break
                    else:
                        cloud_path.pop()
                        arg_path.pop(0)

                        if len(arg_path) == 0:
                            break
                if len(arg_path) > 0:
                    arg_path_str = '/' + '/'.join(arg_path)
                    cloud_path.append(arg_path_str)
                else:
                    cloud_path = ''
            else:
                if self.__object_exists__(self.s3_client, args):
                    self.cloud_wDir = args
                    success = True
                else:
                    success = False
                    err_msg = ('The object at ' + self.cloud_cur_bucket + ':' + args
                                    + ' does not exist or is inaccessible' + os.linesep)
            
            if not cloud_path or cloud_path == '':
                self.cloud_wDir = ''
                success = True
            else:
                cloud_path_str = '/'.join(cloud_path)
                try:
                    self.s3_client.head_object(Bucket=self.cloud_cur_bucket, Key=cloud_path_str)
                    self.cloud_wDir = args
                    success = True
                except ClientError as e:
                    if err_msg == '':
                        err_msg = ('The object at ' + self.cloud_cur_bucket + ':' + cloud_path_str 
                                + ' does not exist or is inaccessible' + os.linesep)
                    success = False

        if not success:
            print('Error:', err_msg, 'Usages:', os.linesep, 'ch_folder <bucket name>', os.linesep,
                    'ch_folder <bucket name>:<full pathname of directory>', os.linesep,
                    'ch_folder <full or relative pathname of local directory>'
                    )

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
