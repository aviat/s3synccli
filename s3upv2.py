#!/usr/bin/env python3
## Sean Landry, sean.d.landry@gmail.com, sean.landry@cellsignal.com
## version 03june2017

"""
Upload to S3 with metadata.

Metadata notes
- for directories use "mode":"509", mode 33204 does NOT work
- for files use "mode":"33204"
- currently these values are hard coded

Usage:
    s3up <localdir> <s3key> [--metadata METADATA]
    s3up -h | --help 

Options: 
    <localdir>               local directory file path
    <s3key>                  s3 key, e.g. cst-compbio-research-00-buc/
    --metadata METADATA      metadata in json format '{"uid":"6812", "gid":"6812", "mode":"33204"}'
    -h --help                show this screen.
""" 

from docopt import docopt
import subprocess
import os
import sys
import json

class SmartSync():

    def __init__(self, local = None, s3path = None, meta = None)
        self.local = local
        self.s3path = s3path
        self.bucket = s3path.split('/', 1)[0]
        self.key = self.parse_prefix(s3path)
        self.localToKeys = self.find_dirs(local)
        self.metadir, self.metafile = self.parse_meta(meta)


    def parse_meta(self, meta = None):
        metadir = json.loads(options['--metadata'])
        metadir["mode"] = "509"
        metadirjs = json.dumps(metadir)
        metafile = json.loads(options['--metadata'])
        metafile["mode"] = "33204"
        metafilejs = json.dumps(metafile)
        return metadirjs, metafilejs

    def parse_prefix(self, path = None):
        if len(path.split('/', 1)) > 1:
            return path.split('/', 1)[1]
        else:
            return path

    def find_dirs(self, local = None):
        ## find local directories and sort
        d = subprocess.Popen(["find", local, "-type", "d"],
                         stdout = subprocess.PIPE, shell = False)

        dsort = subprocess.Popen(["sort", "-n"], stdin = d.stdout, shell = False,
                             stdout = subprocess.PIPE)

        ## sorted directories as a list
        dLst = dsort.communicate()[0].decode().strip().split('\n')
        return [self.key + k[len(self.local) + 1:] + '/' for k in dLst]
        


    def key_exists(self, key = None):
         return subprocess.Popen(["aws", "s3api", "head-object", "--bucket",
                        self.bucket, "--key", key],
                        stdout = subprocess.PIPE, shell = False)

    def meta_check(self, obj_head = None):
        meta = json.loads(obj_head.communicate()[0].decode())['Metadata']

        if len(meta) == 0:
            return False
        else:
            return True

    def meta_update(self, key = None, metadata = None):
        subprocess.run(["aws", "s3api", "copy-object", "--bucket",
                    self.bucket, "--key", key, "--copy-source",
                    self.bucket + "/" + key, "--metadata", metadata,
                    "--metadata-directive", "REPLACE"])

    def create_key(self, key = None, metadata = None): 
        subprocess.run(["aws", "s3api", "put-object", "--bucket", self.bucket,
                            "--key", key, "--metadata", meta])

    def verify_keys(self, keys = None, meta = None)

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
                sys.stderr.write('creating key now...\n')

                self.create_key(key = k, metadata = meta)

                ## debug
                #check = subprocess.Popen(["aws", "s3api", "head-object", "--bucket", 
                #                          self.bucket, "--key", k], 
                #                          stdout = subprocess.PIPE, shell = False)

                #print(json.loads(check.communicate()[0].decode())['Metadata'])



    def smart_sync(self):
        ## verify the s3path passed as command line arg
        self.verify_keys(keys = [self.key], meta = self.metadir)

        ## verify local dirs converted to s3keys
        self.verify_keys(keys = self.localToKeys[1:], meta = self.metadir)

        ## complete sync
        s3url = 's3://' + self.s3path
        subprocess.run(["aws", "s3", "sync", local, s3url])
        

if __name__== "__main__":
    """
    Command line arguments.
    """  

    options = docopt(__doc__)

    s3_sync = SmartSync(local = options['<localdir>'], s3key = options['<s3key'], meta = options['--metadata'])

    s3_sync.smart_sync()
