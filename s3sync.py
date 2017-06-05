#!/usr/bin/env python3
## Sean Landry, sean.d.landry@gmail.com, sean.landry@cellsignal.com
## version 05june2017
## Description: s3syncsli --> sync local directory with s3 bucket.  
##              Contains the SmartS3Sync() class.

"""
Sync local data with S3 maintaining metadata.  This program will accept 
only directories as positional arguments.

Metadata notes
- for directories use "mode":"509", mode 33204 does NOT work
- for files use "mode":"33204"
- currently these values are hard coded in the SmartSync.parse_meta() object 
  method

Usage:
    s3up <localdir> <s3path> [--metadata METADATA --profile PROFILE]
    s3up -h | --help 

Options: 
    <localdir>               local directory file path
    <s3path>                  s3 key, e.g. cst-compbio-research-00-buc/
    --metadata METADATA      metadata in json format [default: {"uid":"6812", "gid":"6812"}]
    --profile PROFILE        aws profile name [default: default]
    -h --help                show this screen.
""" 

from docopt import docopt
import subprocess
import os
import sys
import json

class SmartS3Sync():

    def __init__(self, local = None, s3path = None, meta = None, profile = None):
        self.local = local
        self.s3path = s3path
        self.bucket = s3path.split('/', 1)[0]
        self.key = self.parse_prefix(s3path)
        self.localToKeys = self.find_dirs(local)
        self.metadir, self.metafile = self.parse_meta(meta)
        self.profile = profile


    def parse_meta(self, meta = None):
        """
        Parses passed json argument and adds hardcoded mode for files
        and directories.
        
        Args:
            meta (str): json metadata.

        Returns:
            metadirjs, metafilejs (json): json string specific for dirs and 
                                          files.

        """
        metadir = json.loads(options['--metadata'])
        metadir["mode"] = "509"
        metadirjs = json.dumps(metadir)
        metafile = json.loads(options['--metadata'])
        metafile["mode"] = "33204"
        metafilejs = json.dumps(metafile)
        return metadirjs, metafilejs

    def parse_prefix(self, path = None):
        """
        Parse an s3 prefix key path.

        Args:
            path (str): entire s3 path.

        Returns:
            path (str): path withouth bucket name.

        """
        if len(path.split('/', 1)) > 1:
            return path.split('/', 1)[1]
        else:
            return path

    def find_dirs(self, local = None):
        """
        Execute find and sort subprocceses to identify and sort all local 
        child directories of the local argument.  All directories identified
        are converted to s3 keys.

        Args:
            local (str): full path to local directory.

        Returns:
            (list): s3 keys.

        """
        ## find local directories and sort
        
        d = subprocess.Popen(["find", local, "-type", "d"],
                         stdout = subprocess.PIPE, shell = False)

        dsort = subprocess.Popen(["sort", "-n"], stdin = d.stdout, shell = False,
                             stdout = subprocess.PIPE)

        ## sorted directories as a list
        dLst = dsort.communicate()[0].decode().strip().split('\n')
        return [self.key + k[len(self.local) + 1:] + '/' for k in dLst]
        
    def key_exists(self, key = None):
        """
        Check if an s3 key exists.

        Args:
            key (str): s3 key

        Returns:
            stdout subprocess call to aws s3api head-object

        """
        return subprocess.Popen(["aws", "s3api", "head-object", "--bucket",
                        self.bucket, "--key", key, "--profile", self.profile],
                        stdout = subprocess.PIPE, shell = False)

    def meta_check(self, obj_head = None):
        """
        Parse the metadata for an s3 object.

        Args:
            obj_head (stdout): stdout of subprocess call to aws s3api 
                               head-object.

        Returns:
            boolean: True metadata exists, False no metadata present.

        """
        meta = json.loads(obj_head.communicate()[0].decode())['Metadata']

        if len(meta) == 0:
            return False
        else:
            return True

    def meta_update(self, key = None, metadata = None):
        """
        Update the metadata for an s3 object.

        Args:
            key (str):  s3 key.
            metadata (json str):  metadata to attach to the object.


        """
        subprocess.run(["aws", "s3api", "copy-object", "--bucket",
                    self.bucket, "--key", key, "--copy-source",
                    self.bucket + "/" + key, "--metadata", metadata,
                    "--metadata-directive", "REPLACE", "--profile", 
                    self.profile])

    def create_key(self, key = None, metadata = None): 
        """
        Create an s3 object, also known as put-object.

        Args:
            key (str):  s3 key.
            metadata (json str):  metadata to attach to the object.

        """
        subprocess.run(["aws", "s3api", "put-object", "--bucket", self.bucket,
                            "--key", key, "--metadata", metadata, "--profile", 
                            self.profile])

    def verify_keys(self, keys = None, meta = None):
        """
        Check if the keys in list exist.  If the do not exist create them.

        Args:
            keys (lst): list of keys.
            meta (json str): metadata to attach to the keys
        """
        for k in keys:
            try:
                check = self.key_exists(key = k)

                ## if key does exist check for metadata
                metaresult = self.meta_check(obj_head = check)

                if not metaresult:
                    ## if no metadata then add some now
                    sys.stderr.write('no metadata found for ' + k + ' updating...\n')
                    update = self.meta_update(key = k, metadata = meta)

            except:
                ## key does not exist so lets create it
                sys.stderr.write("creating key '" + k + "'\n")

                self.create_key(key = k, metadata = meta)

                ## debug
                #check = subprocess.Popen(["aws", "s3api", "head-object", "--bucket", 
                #                          self.bucket, "--key", k], 
                #                          stdout = subprocess.PIPE, shell = False)

                #print(json.loads(check.communicate()[0].decode())['Metadata'])



    def sync(self):
        """
        Completes a sync between a local path and s3 bucket path.

        """
        ## verify the s3path passed as command line arg
        self.verify_keys(keys = [self.key], meta = self.metadir)

        ## verify local dirs converted to s3keys
        self.verify_keys(keys = self.localToKeys[1:], meta = self.metadir)

        ## complete sync
        s3url = 's3://' + self.s3path
        subprocess.run(["aws", "s3", "sync", self.local, s3url, "--metadata", 
                         self.metafile, "--profile", self.profile])
        

if __name__== "__main__":
    """
    Command line arguments.
    """  

    options = docopt(__doc__)

    s3_sync = SmartS3Sync(local = options['<localdir>'], 
                        s3path = options['<s3path>'], 
                        meta = options['--metadata'], 
                        profile = options['--profile'])

    s3_sync.sync()
