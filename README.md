# S5 - An AWS S3 Shell
### Thomas Rollins
#

## General Information
- All S3 commands which accept an S3 path assume the given path is in the format `<bucket name>:<Object path>` or
`<realtive object path>` where the current working folder is set (not at the top-level).
- Realtive paths are assumed to follow the `./` represents current working directory and `../` represents up one level from the current working directory.
- All S3 bucket names may only contain lower case alphanumeric characters (`a-z0-9`) and hyphens (`-`).
- All S3 "directory" names may only contain alphanumeric characters (`A-Za-z0-9`) and hyphens (`-`).
- All S3 Object creation/movement assumes a unique object key was given and will overwrite any existing object which matches the key given. It is assumed versioning is not enabled.
- Requires python 3.7.4+
- Tested and functional on Windows 10 and Debian GNU/Linux 10 (buster); should support all operating systems with a standard UNIX posixpath or Windows ntpath which support python 3.7.4+

## Usage
- `python3 ./S5.py`
#

# Avaliable S3 Commands
## General Commands
#
## `cwf`
### Displays the current working folder in S3.
- No Arguments
    
    #### Output :   `<bucket name>:<S3 path>`
    - `/` represents the root (top level)
    ### Example Usage:
        S5> cwf
        rollins_bucket:test/
    ## Note:

##  `list [-l]`
### Displays the contents given path or current working folder.
- Optional Arguments
    - `<bucket name>`
    - `<bucket name>:<S3 path>`
    - `<relative S3 path>` 

    
    #### Output :   `<bucket name>:<S3 Object Key>`
    - `/` represents the root (top level)
    ### Example Usage:
        S5> list rollins_bucket
        test/                              test2/                           test_upload.txt
        rollins_bucket:test/
        S5> list rollins_bucket -l
        Object                             Last Modified                     Owner     Type                        Size (KB)
        test/                              2021-09-30 17:37:20+00:00         None      application/x-directory       0.00
        test2/                             2021-09-30 22:04:06+00:00         None      application/x-directory       0.00
        test_upload.txt                    2021-09-30 17:23:52+00:00         None      binary/octet-stream           0.00
        test_upload_2.txt                  2021-09-30 17:24:41+00:00         None      binary/octet-stream           0.42

    ## Note:
    - When no arguments are given the current working folder is assumed.
    - the detailed output `-l` flag cannot be used on the top level `/`

## `ch_folder <path>`
### Changes the current working folder in S3.
-   `<path>` can be `/` (returns to top layer), a bucket name `<bucket name>:`, a full path `<bucket name>:<S3 path>` or a relative path. *Note that a relative path requires the current working folder to not be in the top level*.

    
    #### Output :  None
    - `/` represents the root (top level)
    ### Example Usage:
        S5> ch_folder rollins_bucket
        S5> ./test
        S5> cwf
        rollins_bucket:test/
    ## Note:
    - In the case where the current working folder is set to a bucket `ch_folder <path>` where `<path>` does not contain a `:` or a relative path with `./` or `../` S5 will try to resolve it as `./<path>`. If the directory does not exist or is inaccessible then it will then silently attempt to resolve `<path>` as a bucket name. To explicity change the current working folder to a new bucket, use: `ch_folder <bucket name>:`

 #

## Bucket Commands
#
## `create_bucket <bucket name> [-r <region>] [-acl <canned ACL>]`
### Creates a new bucket in S3.
-   Bucket names may only contain lowercase alphanumeric characters (`a-z0-9`) and hyphens (`-`)
-   The bucket name must be unique across all regions.
-   if `-acl <canned ACL>` is used the `<canned ACL>` must be a single string without spaces. Refer to https://docs.aws.amazon.com/AmazonS3/latest/userguide/acl-overview.html#canned-acl for avaliable options.
-   if `-r <region>` is used the `<region>` must be one of the regions offered by AWS. Refer to https://docs.aws.amazon.com/general/latest/gr/s3.html#s3_region for avaliable regions.
-   By default `us-east-2` is the region used.
-   By default `private` is the canned ACL used.

    #### Output :  None
    
    ### Example Usage:
        S5> create_bucket rollins_bucket
        S5> create_bucket rollins_bucket-test -r ca-central-1 -acl private
   
## `delete_bucket <bucket name>`
### Deletes an existing empty bucket in S3.
-   The Bucket must be empty

    #### Output :  None
    
    ### Example Usage:
        S5> delete_bucket rollins_bucket


## Object Commands
#
## `create_folder <folder name>`
### Creates a new 'folder' in S3.
-   Folder names may only contain alphanumeric characters or hyphens (`a-zA-Z0-9-`).
-   The folder name may be a relative or absolute S3 path.

    #### Output :  None
    
    ### Example Usage:
        S5> create_folder rollins_bucket:test
        S5> create_folder ./test1/test2/test3/test4/

    ## Note:
    -   Multiple sub-directories can be created at once by seperating each sub-directory with `/`

## `lc_copy <path to local file> [<path to S3 folder>/]<filename.ext>`
### Copies a local file to an S3 location.
-   
    #### Output :  None
    
    ### Example Usage:
        S5> lc_copy ./test.txt rollins_bucket:test.txt
        S5> lc_copy C:\\CIS4010\Assignment_1\test.txt ./dir/test.txt
        S5> lc_copy /mnt/c/CIS4010/Assignment_1/test.txt rollins_bucket:dir/test.txt
    ## Note:
    -   All local paths follow your host operating system's pathing format.
    -   When using a relative path you must explictly use `./` or `../`

## `cl_copy [<path to S3 folder>/]<filename.ext> <path to local file> `
### Copies an S3 object to a local location.
-   
    #### Output :  None
    
    ### Example Usage:
        S5> cl_copy rollins_bucket:test.txt ./test.txt
        S5> cl_copy ./dir/test.txt C:\\CIS4010\Assignment_1\test.txt 
        S5> cl_copy rollins_bucket:dir/test.txt /mnt/c/CIS4010/Assignment_1/test.txt

    ## Note:
    -   All local paths follow your host operating system's pathing format.
    -   When using a relative S3 path you must explictly use `./` or `../`

## `ccopy <path to S3 object> <path to S3 Location>`
### Copies an S3 object to another S3 location.
-   
    #### Output :  None
    
    ### Example Usage:
        S5> ccopy rollins_bucket:test.txt rollins_bucket-2:test.txt
        S5> ccopy ./dir/test.txt ../test.txt

## `cdelete <path to S3 object>`
### Deletes an S3 object or empty S3 folder
-   
    #### Output :  None
    
    ### Example Usage:
        S5> cdelete rollins_bucket:test.txt
        S5> cdelete ./test
    
    ## Note:
    -   A Folder must be empty or the operation will fail
#
## Host System Commands
-   S5 will attempt to directly pass unrecongized commands to the host operating system's default terminal and output the result.
        
    ### Example Usage:
        S5> ping google.ca
        
        Pinging google.ca [172.217.1.3] with 32 bytes of data:
        Reply from 172.217.1.3: bytes=32 time=23ms TTL=116
        Reply from 172.217.1.3: bytes=32 time=35ms TTL=116
        Reply from 172.217.1.3: bytes=32 time=21ms TTL=116
        Reply from 172.217.1.3: bytes=32 time=26ms TTL=116

        Ping statistics for 172.217.1.3:
            Packets: Sent = 4, Received = 4, Lost = 0 (0% loss),
        Approximate round trip times in milli-seconds:
            Minimum = 21ms, Maximum = 35ms, Average = 26ms
    ## Note:
    -   Deleting the last object in a directory will also delete the directory.