import os
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

    def is_valid_credentials(self):
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

    def __bucket_exists__(self, name) -> list:
        try: 
            self.s3_resource.meta.client.head_bucket(Bucket=name)
        except ClientError as e:
            # logging.error(err)
            return [False, e.response['Error']['Message']]
        except BotoCoreError:
            return [False, 'Invalid Params']
        return [True, None]

    def __object_exists__(self, bucket_name, object_path) -> bool:
        try:
            self.s3_client.head_object(Bucket=self.cloud_cur_bucket, Key=object_path)
            return True
        except ClientError as e:
            return False

    def __is_cloud_dir__(self, bucket_name, object_path) -> bool:
        try:
            bucket = self.s3_resource.Bucket(bucket_name)
            for object_summary in bucket.objects.filter(Prefix=object_path):
                return True
        except ClientError as e:
            pass
        return False

    
    def __resolve_cloud_path__(self, raw_path, is_dir):
        bucket_name = ''
        key = ''
        if not raw_path.strip():
            if self.cloud_cur_bucket == '/':
                return [False, self.cloud_cur_bucket, key, 'The top level is not a bucket.']
            else:
                result = self.__bucket_exists__(self.cloud_cur_bucket)
                result[1] = self.cloud_cur_bucket
                result.insert(2, self.cloud_wDir)
                result.append('')
                return result
        elif ':' in raw_path:
            try:
                path = raw_path.split(':', 1)
                bucket_name = path[0]
                key = path[1]
                if is_dir and not self.__is_cloud_dir__(bucket_name, key):
                    return [False, bucket_name, key, 'Directory does not Exist']
                else:
                    return [True, bucket_name, key, '']
            except IndexError or TypeError or ValueError:
                return [False, bucket_name, key, 'Invalid arguments']
        elif './' in raw_path or '../' in raw_path:
            result = self.__resolve_relative_path__(raw_path)
            result.insert(1, self.cloud_cur_bucket)
            if is_dir:
                if not self.__is_cloud_dir__(result[1], result[2]):
                    result[0] = False
                    result.append('Directory does not exist')
                    return result
            if result[2].startswith('/'):
               result[2] = result[2][1:] #remove first char
            return result
        elif not self.cloud_cur_bucket == '/':
            if self.__is_cloud_dir__(self.cloud_cur_bucket, raw_path):
                return [True, self.cloud_cur_bucket, raw_path, '']
            else:
                result = self.__bucket_exists__(raw_path)
                if result[0]:
                    return [True, raw_path, '', '']
                else:
                    return [False, self.cloud_cur_bucket, raw_path, self.cloud_cur_bucket + ':' + raw_path + ' is not a valid directory or bucket; or you do not have permission to access it.']
        else:
            key = ''
            result = self.__bucket_exists__(raw_path)
            if result[0]:
                return [True, raw_path, '', '']
            else:
                return [False, raw_path, '', result[1]]

    def __resolve_relative_path__(self, path):
        if not path:
            return [True, self.cloud_wDir]
        arg_path = path.split('/')
        arg_path[:] = [x for x in arg_path if x.strip()]
        cloud_dir = self.cloud_wDir
        cloud_path = cloud_dir.split('/')
        cloud_path[:] = [x for x in cloud_path if x.strip()]
        if arg_path[0] == '.':
            arg_path.pop(0)
            if len(arg_path) == 0:
                return [True, self.cloud_wDir]
            else:
                arg_path_str = '/'.join(arg_path)
                cloud_path.append(arg_path_str)
                return [True, '/'.join(cloud_path)]
                
        elif arg_path[0] == '..':
            while arg_path[0] == '..':
                if len(cloud_path) == 0:
                    err_msg = 'Invalid Arguments: cannot go beyond the top-layer of the bucket.'
                    return [False, err_msg]
                else:
                    cloud_path.pop()
                    arg_path.pop(0)
                    if len(arg_path) == 0:
                        break
            if len(arg_path) > 0:
                arg_path_str = '/'.join(arg_path)
                if len(cloud_path) == 0:
                    return [True, arg_path_str]
                else:
                    cloud_path.append(arg_path_str)
                    return [True, '/' + '/'.join(cloud_path)]
            else:
                return [True, '']
        else:
            if not path.endswith('/'):
                path += '/'
            return [True, path]
        
    # usa-east-1 will return None
    def get_location(client, bucket_name) -> str:
        response = client.get_bucket_location(Bucket=bucket_name)
        return response['LocationConstraint']

    def do_lc_copy(self, args):
        success = False
        err = None
        key = None
        if len(args) < 2:
            success = False
            err = 'Invalid number of arguments.'
        else:
            abs_local_path = self.get_abs_local_path(args[0])

            if(abs_local_path == None or not os.path.exists(abs_local_path)):
                success = False
                err = args[0] + ' does not exist or is inaccessible.'
            else:
                try:
                    result = self.__resolve_cloud_path__(args[1], False)
                    if result[0]:
                        bucket_name = result[1]
                        key = result[2]
                    else:
                        err = result[3]
                        success = False
                except IndexError or ValueError:
                    success = False
                if err == None:
                    if not key or key == '' or bucket_name == '/':
                        err = 'Invalid cloud path'
                    try:
                        if key.endswith('/'):
                            key = key[:-1]
                        response = self.s3_client.upload_file(abs_local_path, bucket_name, key)
                        success = True
                    except ClientError as e:
                        err_code = e.response['Error']['Code']
                        err = 'Error: ' + err_code + ' ' + e.response['Error']['Message']
                        success = False
        if err != None: 
            print('Error:', err, os.linesep, 'Usage:', os.linesep, 'lc_copy <path of local file> <bucket name>:<full path of s3 object>')
        return 0 if success else 1

    def do_cl_copy(self, args):
        success = False
        err = None
        if len(args) < 2:
            success = False
            err = 'Invalid number of arguments.'
        else:
            abs_local_path = self.get_abs_local_path(args[1])
            if abs_local_path and os.path.exists(abs_local_path):
                success = False
                err = args[1] + ' already exists.'
            else:
                if not abs_local_path:
                    abs_local_path = os.path.normpath(os.path.join(self.local_wDir, (args[1])))
                if os.path.isdir(os.path.split(abs_local_path)[0]):
                    try:
                        result = self.__resolve_cloud_path__(args[0], False)
                        if result[0]:
                            bucket_name = result[1]
                            key = result[2]
                        else:
                            err = result[3]
                            success = False
                    except IndexError or ValueError:
                        success = False
                    if err == None:
                        if not key or key == '' or bucket_name == '/':
                            err = 'Invalid cloud path'
                        else:
                            if key.endswith('/'):
                                key = key[:-1]
                            try:
                                response = self.s3_client.download_file(bucket_name, key, abs_local_path)
                                success = True
                            except ClientError as e:
                                err_code = e.response['Error']['Code']
                                err = 'Error: ' + err_code + ' ' + e.response['Error']['Message']
                                success = False
                else:
                    err = os.path.split(abs_local_path)[0] + ' does not exist or is inaccessible.'
        if err != None: 
            print('Error:', err, os.linesep, 'Usage: cl_copy <path of s3 object> <path of local file>')
        return 0 if success else 1



    def do_create_bucket(self, args):
        err = None
        success = False
        pattern = re.compile('^[a-z0-9-]*$')
        
        #default
        region = 'us-east-2'
        bucket_name = None
        acl = 'private'

        if '-r' in args:
            region = args[args.index('-r') + 1]
            args.remove('-r')
        
        if '-acl' in args:
            acl = args[args.index('-acl') + 1]
            args.remove('-acl')

        
        bucket_name = args[0]
        
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
        # cannot start with a `/` and cannot have a `/` followed by another.
        # all characters must be alphanumeric or a hyphen with the exception of a single slash seperator
        # it may end in `/` but does not have to
        # it does not need to contain a slash
        pattern = re.compile(r'^[a-zA-Z\d-]+((/([a-zA-Z\d-])+))*?/?$')
        args[:] = [x for x in args if x.strip()]
        success = False
        err = None
        key = ''
        if args == None or '/' in args:
            err = 'Invalid Arguments' + os.linesep
            success = False
        else:
            result = self.__resolve_cloud_path__(args[0], True)
            if result[0]:
                success = False
                err = 'The current directory already exists'
            elif self.__bucket_exists__(result[1]):
                success = True
                key = result[3]
            else:
                success = False
                err = 'The bucket ' + result[1] + ' is not accessible or does not exist'
        if success:
            if re.match(pattern, key):
                try:
                    response = self.s3_client.put_object(Bucket=result[1], Key=key)
                    success = True
                except ClientError as e:
                    success = False
                    err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
            else:
                err = 'Invalid S3 Path. Folder names may only contain alphanumeric characters or hyphens (`a-zA-Z0-9-`).'
        if err:
            print('Error:', err, os.linesep, 'Usage: create_folder <bucket name>:<full path of folder>')

        return 0 if success else 1

    # evaluate if folder exists using s3.Object('bucket', 'object name').load()
    # if at root and there is no : then it must be a bucket
    # ch_folder bucket_name: goes directly to a new bucket?
    def do_ch_folder(self, args):
        args[:] = [x for x in args if x.strip()]
        success = False
        err = None
        if args == None  or  ' ' in args:
            err = 'Invalid Arguments' + os.linesep
            success = False
        
        #go back to top-level
        elif args[0] == '/':
            self.cloud_cur_bucket = '/'
            self.__set_cur_cloud_dir__(None)
            success = True
            return 0
        else:
            result = self.__resolve_cloud_path__(args[0], True)
            if result[0]:
                self.cloud_cur_bucket = result[1]
                if result[2] == None:
                   self.__set_cur_cloud_dir__(None)
                else:
                    self.__set_cur_cloud_dir__(result[2])
                success = True
            else:
                success = False
                err = result[3]

        if not success:
            if self.cloud_cur_bucket == '/':
                usage_msg = ('Usages:' +  os.linesep + ' ch_folder <bucket name>' + os.linesep +
                            ' ch_folder <bucket name>:<full pathname of directory>' + os.linesep +
                            ' ch_folder <full or relative pathname of local directory>')                
            else:
                usage_msg = ('Usages:' + os.linesep + ' ch_folder <bucket name>' + os.linesep +
                            ' ch_folder <bucket name>:<full pathname of directory>' + os.linesep +
                            ' ch_folder <full or relative pathname of local directory>')
            print('Error: ', err, os.linesep + usage_msg)

        return 0 if success else 1

    def do_cwf(self, args):
        if(self.cloud_wDir == ''):
            print(self.cloud_cur_bucket)
        else :
            print(self.cloud_cur_bucket + ':' + self.cloud_wDir)
        return 0

    def do_list(self, args):
        success = False
        err = None
        bucket_name = ''
        key = ''
        objs = []
        is_detailed = False

        if not args or args[0] == None:
            bucket_name = self.cloud_cur_bucket
            key = self.cloud_wDir
        else:
            if '-l' in args:
                is_detailed = True
                args.remove('-l')
            if len(args) < 1 and self.cloud_cur_bucket == '/':
                result = [False, None, None, 'Cannot give detailed output of top-level.']
            else:
                result = self.__resolve_cloud_path__('/'.join(args), True)
            if result[0]:
                bucket_name = result[1]
                key = result[2]
                if key == None or key == '':
                    key = ''
                elif not key.endswith('/'):
                    key += '/'
            else:
                err = result[3]
        
        if not err:
            try:
                if bucket_name == '/':
                    objs = [obj.name for obj in self.s3_resource.buckets.all()]
                    success = True
                else:
                    bucket = self.s3_resource.Bucket(bucket_name)
                    objs = [obj.key for obj in bucket.objects.filter(Prefix=key)]
                    
                    success = True
            except ClientError as e:
                err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
                success = False
            except ParamValidationError:
                err = 'Invalid argumnets'
                success = False

        if success:
            obj_dict = []
            for obj in objs:
               obj_dict.append({'is_valid': True, 'key': obj, 'path': obj})

            for i in range(len(obj_dict)):
                if key and not key == '':
                    index = obj_dict[i]['path'].find(key)
                    if index >= 0:
                        obj_dict[i]['path'] = obj_dict[i]['path'][index + len(key):]

                if obj_dict[i]['path'].count('/') == 2:
                    index = obj_dict[i]['path'].find('/')
                    obj_dict[i]['path'] = obj_dict[i]['path'][:- len(obj_dict[i]['path']) + index + 1]

                elif obj_dict[i]['path'].count('/') == 1:
                    if not obj_dict[i]['path'].endswith('/'):
                        obj_dict[i]['path'] = obj_dict[i]['path'].split('/', 1)[0] + '/'
                    # else:
                    #     obj_dict[i]['is_valid'] = False
            
                if not obj_dict[i]['path'].strip() or obj_dict[i]['path'].count('/') > 1:
                    obj_dict[i]['is_valid'] = False
                # invalidate entries with the same path
                for k in range(0, i):
                    if obj_dict[i]['path'] == obj_dict[k]['path']:
                        obj_dict[i]['is_valid'] = False

            # remove all invalid items
            obj_dict = [item for item in obj_dict if item['is_valid']]

            if len(obj_dict) == 0:
                print('There are no items to display.')
            elif is_detailed:
                    #this tabular format code will break easily given inputs outside the defined ranges below
                    print('%-35s' % 'Object' + '%-34s' % 'Last Modified' + '%-10s' % 'Owner' + '%-28s' % 'Type' + '%8s' % 'Size (KB)')   
                    for i in range(len(obj_dict)):
                        obj_key = ''
                        last_mod = ''
                        size = 0.0
                        owner = ''
                        obj_type = ''
                        if obj_dict[i]['is_valid']:
                            try:
                                # get summary
                                object_summary = self.s3_resource.ObjectSummary(bucket_name, obj_dict[i]['key'])
                                obj_key = obj_dict[i]['path']
                                last_mod = object_summary.last_modified
                                size = round(object_summary.size / 1024, 2)
                                owner = object_summary.owner
                                #load content type and other (unused) attributes 
                                object_summary = object_summary.get()
                                obj_type =  object_summary['ContentType']
                                # trim charset info
                                obj_type = obj_type.split(';', 1)[0]
                                
                            except ClientError as e:
                                    err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
                                    success = False
                            if not err:  
                                print('%-35s' % obj_key + '%-34s' % last_mod + '%-10s' % owner + '%-28s' % obj_type + '%6.2f' % size)
            #this tabular format code will break easily given inputs > 30 characters in length or if the output window's width is less than the total line length                 
            else: 
                
                if len(obj_dict) >= 3:
                    while not len(obj_dict) % 3 == 0:
                        obj_dict.append({'is_valid': False, 'key': '', 'path': ''})
                    for col1, col2, col3 in zip(obj_dict[::3], obj_dict[1::3], obj_dict[2::3]):
                        print('{:<35}{:<30}{:<}'.format(col1['path'], col2['path'], col3['path']))
                else:
                    for obj in obj_dict:
                        print('{:<35}'.format(obj['path']), end='')

        if not success:
            if err == 'Not Found':
                print('Error:', err, os.linesep, 'The S3 Resource does not exist or is inaccessible.',  os.linesep, 'Usage: list')
            else:
                print('Error:', err, os.linesep, 'Usage: list <path to S3 Bucket or Directory>')
        print('') #force a new line
        return 0 if success else 1

    def do_ccopy(self, args):
        args[:] = [x for x in args if x.strip()]
        success = False
        err = None
        src = []
        dest = []
        if args == None  or not len(args) == 2:
            err = 'Invalid Arguments' + os.linesep
            success = False
        else:
            result = self.__resolve_cloud_path__(args[0], False)
            src.append(result[1])
            src.append(result[2])
           
            result = self.__resolve_cloud_path__(args[1], True)
            dest.append(result[1])
            dest.append(result[2])
            err = result[3]
            copy_src = {'Bucket' : src[0], 'Key' : src[1]}
            try:
                self.s3_resource.meta.client.copy(copy_src, dest[0], dest[1])
                success = True
            except ClientError as e:
                if not err or err == '':
                    err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
       
        if not success:
             print('Error:', err, os.linesep, 'Usage: ccopy <source S3 location of object> <destination S3 location>')
        return 0 if success else 1

    def do_cdelete(self, args):
        args[:] = [x for x in args if x.strip()]
        success = False
        err = None
        if args == None or not len(args) == 1:
            err = 'Invalid Arguments' + os.linesep
            success = False
        else:
            result = self.__resolve_cloud_path__(args[0], True)
            if not result[0]:
                success = False
                err = result[3]
        
        if not err:
            bucket_name = result[1]
            key = result[2]
            try:
                bucket = self.s3_resource.Bucket(bucket_name)
                objects = [object.key for object in bucket.objects.filter(Prefix=key)]
            except ClientError as e:
                err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
            
            if len(objects) <=2:
                if key in objects:
                    try:
                        self.s3_resource.Object(bucket_name, key).delete()
                        success = True
                    except ClientError as e:
                        err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
                elif len(objects) == 1 and  objects[0].endswith('/'):
                    try:
                        bucket.objects.filter(Prefix=objects[0]).delete()
                        success = True
                    except ClientError as e:
                        err = e.response['Error']['Code'] + '. ' + e.response['Error']['Message']
                elif len(objects) == 1:
                    err = ' '.join(args) + ' is not an empty folder.'
                else:
                    err = ' '.join(args) + ' does not exist or is inaccessible.'
            else:
                err = ' '.join(args) + ' is not empty.'
            
        if not success:
             print('Error:', err, os.linesep, 'Usage: cdelete <path to S3 object>')

        return 0 if success else 1
        
    def do_delete_bucket(self, args):
        success = False
        if not len(args) == 1:
            success = False
            err = 'Invalid number of arguments.'
        elif self.cloud_cur_bucket == args[0]:
            err = 'Cannot delete your current working bucket (try \'ch_folder /\' first).'
            success = False
        else:
            try:
                response = self.s3_client.delete_bucket(Bucket=args[0])
                success = True
            except ClientError as e:
                err = e.response['Error']['Code'] + ' ' + e.response['Error']['Message']
                success = False
        if not success:
            print('Error:', err, os.linesep, 'Usage: delete_bucket <bucket name>')

        return 0 if success else 1


