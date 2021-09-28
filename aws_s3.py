import os
from typing import Type
from botocore.exceptions import BotoCoreError, ClientError, ParamValidationError     #Error handling
import boto3
import configparser
import re

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

    def __create_S3_resource__(self, session):
        s3 = session.resource('s3')
        return s3

    def __create_S3_client__(self, session):
        s3 = session.client('s3')
        return s3

    def __bucket_exists__(self, resource, name) -> list:
        try: 
            resource.meta.client.head_bucket(Bucket=name)
        except ClientError as err:
            # logging.error(err)
            return [False, int(err.response['Error']['Code'])]
        except BotoCoreError:
            return [False, 'Invalid Params']
        return [True, None]

    def __object_exists__(self, client, object_path) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.cloud_cur_bucket, Key=object_path)
            return True
        except ClientError as e:
            return False

    def __resolve_relative_path__(self, path):
        arg_path = path.split('/')
        arg_path[:] = [x for x in arg_path if x.strip()]
        cloud_dir = self.cloud_wDir
        cloud_path = cloud_dir.split('/')
        cloud_path[:] = [x for x in cloud_path if x.strip()]
           
        if arg_path[0] == '.':
            arg_path.pop(0)
            if len(arg_path) == 0:
                return True, self.cloud_wDir
            else:
                arg_path_str = '/'.join(arg_path)
                if not cloud_path[-1].endswith('/'):
                    cloud_path[-1] += '/'
                return True, '/'.join(cloud_path)
                
        elif arg_path[0] == '..':
            while arg_path[0] == '..':
                if len(cloud_path) == 0:
                    err_msg = 'Invalid Arguments: cannot go beyond the top-layer of the bucket.'
                    return False, err_msg
                else:
                    cloud_path.pop()
                    arg_path.pop(0)

                    if len(arg_path) == 0:
                        break
            if len(arg_path) > 0:
                arg_path_str = '/' + '/'.join(arg_path)
                return True, '/'.join(cloud_path.append(arg_path_str))
            else:
                return True, ''
        else:
            if not path.endswith('/'):
                path += '/'
            return True, path
        
    # usa-east-1 will return None
    def get_location(client, bucket_name) -> str:
        response = client.get_bucket_location(Bucket=bucket_name)
        return response['LocationConstraint']

    def do_lc_copy(self, args):
        success = False
        err = None
        if args == None:
            success = False
            err = 'Invalid number of arguments.'
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
                except IndexError or ValueError:
                    success = False
                if self.__bucket_exists__(self.s3_resource, bucket_name)[0] :
                    try:
                        response = self.s3_client.upload_file(abs_local_path, bucket_name, cloud_path)
                        success = True
                    except ClientError as e:
                        err_code = e.response['Error']['Code']
                        err = 'Error: ' + err_code
                        success = False
                else:
                    err = 'Bucket ' + bucket_name + ' does not exist'
                    success = False
        if err != None: 
            print('Error:', err, os.linesep, 'Usage: lc_copy <path of local file> <bucket name>:<full path of s3 object>')
        return 0 if success else 1
        
    def do_cl_copy(self, args):
        print('Cloud copy:', args)
        success = False
        err = None

        if args == None:
            success = False
            err = 'Invalid number of arguments.'
        else:
            args_list = args.split(' ')
        
        if len(args_list) != 2:
            success = False
            'Invalid number of arguments.'
        else:
            abs_path = self.get_abs_local_path(args_list[1])
            if ':' in args_list[0]:
                try:
                    bucket_path = args_list[0].split(':', 1)
                    result = self.__bucket_exists__(self.s3_resource, bucket_path[0])
                    if result[0]:
                        try:
                            response = self.s3_client.download_file(bucket_path[0], bucket_path[1], abs_path)
                            success = True
                        except ClientError as e:
                            err_code = e.response['Error']['Code']
                            err = 'Error: ' + err_code + ' Failed to download file:', args
                            success = False
                    else:
                        err = 'The bucket', bucket_path[0], 'does not exist or is inaccessible.'
                except IndexError:
                    success = False
        if err != None: 
            print('Error:', err, os.linesep, 'Usage:', os.linesep, 'cl_copy <bucket name>:<full pathname of S3 File> <path to local file>', os.linesep, 'cl_copy <pathname of S3 File> <path to local file>')
        return 0 if success else 1

    def do_create_bucket(self, args):
        print('create a bucket:', args)
        err = None
        success = False
        pattern = re.compile('^[a-z0-9-]*$')
        
        #default
        region = 'ca-central-1'
        bucket_name = None
        acl = 'private'

        try:
            args_list = args.split(' ')
            if '-l' in args_list:
                region = args_list[args_list.index('-l') + 1]
                print(region)
        except IndexError:
            pass
        except ValueError:
            pass

        if len(args_list) > 1:
            bucket_name = args_list[0]
        else:
            bucket_name = args

        if re.match(pattern, bucket_name):
            try:
                self.s3_client.create_bucket(ACL=acl, Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
                success = True
            except self.s3_client.exceptions.BucketAlreadyExists:
                pass
            except ClientError as e:
                success = False
                err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
        else:
            success = False
            err = 'Invalid bucket name. Bucket names contain only lowercase letters, numbers, and/or hyphens.'

        if err != None:
            print('Error:', err, os.linesep, 'Usage: create_bucket <bucket name> Optional Params: -l <location>')

        return 0 if success else 1

    def do_create_folder(self, args):
        print('create folder', args)
        success = False
        err = None

        if ':' in args:
            arg_list = args.split(':')
            try:
                folder_bucket = arg_list[0]
                folder_path = arg_list[1]
                if not folder_path.endswith('/'):
                    folder_path += '/'
                result = True
            except IndexError:
                err = 'Invalid arguments.'
                result = False
        else:
            if not self.cloud_cur_bucket == '/':
                folder_bucket = self.cloud_cur_bucket
                result, msg = self.__resolve_relative_path__(args)
        print('folder bucket:', folder_bucket, 'folder path:', folder_path)
        if result:          
            try:
                response = self.s3_client.put_object(Bucket=folder_bucket, Key=folder_path)
                success = True
            except ClientError as e:
                success = False
                err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
        else:
            success = False
            err = msg
        if err != None:
            print('Error:', err, os.linesep, 'Usage: create_folder <bucket name>:<full path of folder>')

        return 0 if success else 1

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
                        if not bucket_path[1].endswith('/'):
                            bucket_path[1] += '/'
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
            except IndexError or TypeError:
                success = False
        #relative path
        elif self.cloud_cur_bucket != '/':
            status, msg = self.__resolve_relative_path__(args)
            if status:
                if not msg or msg == '':
                    self.cloud_wDir = ''
                    success = True
                else:
                    try:
                        self.s3_client.head_object(Bucket=self.cloud_cur_bucket, Key=msg)
                        self.cloud_wDir = msg
                        success = True
                    except ClientError as e:
                        if err_msg == '':
                            err_msg = ('The object at ' + self.cloud_cur_bucket + ':' + msg 
                                    + ' does not exist or is inaccessible' + os.linesep)
                        success = False
            else:
                err_msg = msg
                success = False
        else:
            result = self.__bucket_exists__(self.s3_resource, args)
            if result[0]:
                self.cloud_cur_bucket = args
                self.cloud_wDir = ''
                success = True
            else:
                err_msg = 'The bucket: ' + args + ' does not exist or is inaccessible' + os.linesep
        if not success:
            if self.cloud_cur_bucket == '/':
                usage_msg = ('Usages:' +  os.linesep + ' ch_folder <bucket name>' + os.linesep +
                            ' ch_folder <bucket name>:<full pathname of directory>' + os.linesep +
                            ' ch_folder <full or relative pathname of local directory>')                
            else:
                usage_msg = ('Usages:' + os.linesep + ' ch_folder <bucket name>:' + os.linesep +
                            ' ch_folder <bucket name>:<full pathname of directory>' + os.linesep +
                            ' ch_folder <full or relative pathname of local directory>')
            print('Error: ', err_msg, usage_msg)

        return 0 if success else 1

    def do_cwf(self, args):
        if(self.cloud_wDir == ''):
            print(self.cloud_cur_bucket)
        else :
            print(self.cloud_cur_bucket + ':' + self.cloud_wDir)
        return 0

    def do_list(self, args):
        print('list buckets', args)
        success = False
        err = ''
        bucket_name = ''
        key = ''
        objs = []
        if args == None or args.rstrip(None) == '':
            bucket_name = '/'
        elif ':' in args:
            args_list = args.split(':', 1)
            bucket_name = args_list[0]
            key = args_list[1]
            if not key.endswith('/'):
                key += '/'
        else:
            bucket_name = args
            key = ''

        if err == '':
            try:
                if bucket_name == '/':
                    objs = [obj.name for obj in self.s3_resource.buckets.all()]
                    success = True
                else:
                    bucket = self.s3_resource.Bucket(bucket_name)
                    objs = [obj.key for obj in bucket.objects.filter(Prefix=key)]
                    print(objs)
                    success = True
            except ClientError as e:
                err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
                success = False
            except ParamValidationError:
                err = 'Invalid argumnets'
                success = False

        if success:
            if len(objs) > 3:
                for col1, col2, col3 in zip(objs[::3], objs[1::3], objs[2::3]):
                    print('{:<25}{:<25}{:<}'.format(col1, col2, col3))
            else:
                for obj in objs:
                    print('{:<25}'.format(obj), end='')


        if not success:
            print('Error:', err, os.linesep, 'Usage: list')
        return 0 if success else 1

    def do_ccopy(self, args):
        print('copy from s3 loc to s3 loc')
        err = ''
        success = False
        src = []
        dest = []
        try:
            args_list = args.split(' ')
            if len(args_list) != 2:
                err = 'Invalid number of arguments.'
            else:
                if ':' in args_list[0]:
                    src = args_list[0].split(':', 1)
                else:
                    src[0] = self.cloud_cur_bucket
                    result, msg = self.__resolve_relative_path__(args_list[0])
                    if result:
                        src[1] = msg
                    else:
                        success = False
                        err = msg
                if ':' in args_list[1]:
                    dest = args_list[1].split(':', 1)
                else:
                    dest[0] = self.cloud_cur_bucket
                    result, msg = self.__resolve_relative_path__(args_list[1])
                    if result:
                        dest[1] = msg
                    else:
                        success = False
                        err = msg
                if not err:
                    copy_src = {'Bucket' : src[0], 'Key' : src[1]}
                    try:
                        self.s3_resource.meta.client.copy(copy_src, dest[0], dest[1])
                        success = True
                    except ClientError as e:
                        err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
        except IndexError or TypeError:
            err = 'Index or Type error'
            success = False
        
        if not success:
             print('Error:', err, os.linesep, 'Usage: ccopy <source S3 location of object> <destination S3 location>')
        return 0 if success else 1

    def do_cdelete(self, args):
        print('delete s3 object', args)
        err = ''
        success = False

        if ':' in args:
            args_list = args.split(':', 1)
            bucket_name = args_list[0]
            key = args_list[1]
        else:
            bucket_name = self.cloud_cur_bucket
            result, msg = self.__resolve_relative_path__(args)
            if result:
                key = msg
            else:
                success = False
                err = msg
        
        if err == '':
            try:
                bucket = self.s3_resource.Bucket(bucket_name)
            except ClientError as e:
                err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
            count = 0
            for objects in bucket.objects.filter(Prefix=key):
                count += 1
            
            if count <= 1:
                try:
                    self.s3_resource.Object(bucket_name, key).delete()
                    success = True
                except ClientError as e:
                    err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
            else:
                err = args + ' is not empty.'
            
        if not success:
             print('Error:', err, os.linesep, 'Usage: cdelete <path to S3 object>')

        return 0 if success else 1
        
    def do_delete_bucket(self, args):
        print('delete bucket', args)
        success = False
        if self.cloud_cur_bucket == args:
            err = 'Cannot delete your current working bucket (try \'ch_folder /\').'
            success = False
        else:
            try:
                response = self.s3_client.delete_bucket(Bucket=args)
                success = True
            except ClientError as e:
                err = e.response['Error']['Code'] + ' ' + e.response['Error']['Message']
                success = False
        if not success:
            print('Error:', err, os.linesep, 'Usage: cdelete <path to S3 object>')

        return 0 if success else 1


