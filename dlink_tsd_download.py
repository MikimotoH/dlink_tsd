#!/usr/bin/env python3
# coding:utf-8
import sqlite3
import re
from web_utils import firefox_url_req
from web_utils import get_http_resp_content_bin
from web_utils import get_http_resp_content
from urllib import request,parse
from os import path
import os
import shutil
import sys
import hashlib
import urllib
import pycurl
import subprocess
from subprocess import Popen
from subprocess import PIPE
from subprocess import call


def uprint(msg:str):
    sys.stdout.buffer.write((msg+'\n').encode('utf8'))

def sha1(data)->str:
    return hashlib.sha1(data).hexdigest()

def getFileSha1(fileName)->str:
    with open(fileName,mode='rb') as fin:
        data = fin.read()
        return sha1(data)

def sql(query:str, var=None):
    global conn
    csr=conn.cursor()
    csr.execute(query, var)
    if not query.upper().startswith("SELECT"):
        conn.commit()

def safeFileName(name:str)->str:
    def pq(x):
        return ''.join('%%%02X'%_ for _ in x.encode('utf-8'))
    bb =re.compile(r"[a-z0-9\-_.]",flags=re.IGNORECASE)
    return ''.join(_ if bb.match(_) else pq(_) for _ in name)

conn=None
dlDir=path.abspath('firmware_files/')

class MyHTTPRedirectHandler(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        self.location = ""
    def http_error_302(self, req, fp, code, msg, headers):
        """store "Location" HTTP response header
        :return: http
        """
        #uprint("req.headers=" + str(req.headers))
        #uprint("headers=" + str(headers))
        #uprint("fp.headers=" + str(fp.headers))
        self.location = headers.get('Location', '')
        print("headers['Location']=" + self.location)
        # print("headers['Set-Cookie']=" + headers.get('Set-Cookie', ''))
        # if headers.get('Set-Cookie'):
        #     if 'Cookie' in req.headers:
        #         req.headers['Cookie'] += \
        #             ('; ' + Cookie(x=headers.get('Set-Cookie')).nvpair())
        try:
            self.location.encode('ascii')
        except UnicodeEncodeError:
            scheme, netloc, path, params, query, fragment = \
                urllib.parse.urlparse(self.location)
            self.location = urllib.parse.urlunparse((
                scheme, netloc, urllib.parse.quote(path), params, query,
                fragment))
            headers.replace_header('Location', self.location)
        return urllib.request.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)
    http_error_301 = http_error_303 = http_error_307 = http_error_302


def downloadFile(url:str, fname:str, chunkSize:int=2*1024*1024):
    opener = urllib.request.build_opener(MyHTTPRedirectHandler)
    urllib.request.install_opener(opener)
    with request.urlopen(firefox_url_req(url)) as resp:
        print("resp_headers=%s"%(resp.info().items()),flush=True)
        with open(fname+".part", mode='wb') as fout:
            while True:
                data=resp.read(chunkSize)
                print('.',end='',flush=True)
                if not data:
                    print('',flush=True)
                    os.rename(fname+".part", fname)
                    return
                fout.write(data)
                fout.flush()

def main():
    startIdx = int(sys.argv[1]) if len(sys.argv)>1 else 0
    global conn
    with sqlite3.connect('dlink_tsd.sqlite3') as conn:
        csr=conn.cursor()
        rows=csr.execute("SELECT href,file_name,file_sha1 FROM dlink "
                "LIMIT -1 OFFSET %d"%startIdx).fetchall()
        for idx, row in enumerate(rows,startIdx):
            href,file_name,file_sha1=row
            print('idx=',idx)
            try:
                dnn=re.search(r"dnn\('(.+)'\)",href).group(1)
            except:
                print('no dnn in href="%s" WHERE file_name="%s"'
                        %(href,file_name))
                continue
            url='http://tsd.dlink.com.tw/asp/get_file.asp?sno='+dnn
            print('url=',url)
            fname = safeFileName(file_name)
            uprint('download "%s" as "%s"'%(file_name,fname))
            if path.exists(path.join(dlDir,fname)) and\
                    path.getsize(path.join(dlDir,fname)) >0 and\
                    bool(file_sha1):
                print('"%s" already exists, bypass!'%fname)
                continue

            try:
                #       Popen("curl -ivvv -L -o '%s' '%s' "%(fname,url),
                #               stdout=sys.stdout, stderr=sys.stderr, 
                #               shell=True)
                #  with open(fname, mode='wb') as fout:
                #      def mywrite(data):
                #          fout.write(data)
                #          fout.flush()
                #          print('.',end='',flush=True)

                #      c=pycurl.Curl()
                #      c.setopt(c.URL, url)
                #      c.setopt(c.WRITEFUNCTION, mywrite)
                #      c.setopt(c.FOLLOWLOCATION,True)
                #      c.perform()
                #      c.close()
                #      print('',flush=True)
                # def hooker(arg_blocknum,arg_bs,arg_size):
                #     print('.',end='',flush=True)
                # request.urlretrieve(url, fname, hooker)
                # print('',flush=True)
                downloadFile(url, fname)
            except Exception as ex:
                print(ex)
                import traceback; traceback.print_exc()
                continue
            
            sha1=getFileSha1(fname)
            print('sha1 %s for "%s"'%(sha1,fname))
            csr.execute("UPDATE dlink SET file_sha1=:sha1 "
                "WHERE file_name=:file_name",locals())
            conn.commit()
            
if __name__=='__main__':
    main()
