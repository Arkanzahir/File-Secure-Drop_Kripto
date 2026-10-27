import base64
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server

class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_data=server.DATA;cls.temp=tempfile.TemporaryDirectory()
        server.DATA=Path(cls.temp.name);server.init_db()
        cls.http=ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.thread=threading.Thread(target=cls.http.serve_forever,daemon=True);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.http.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown();cls.http.server_close();cls.thread.join()
        server.DATA=cls.old_data;cls.temp.cleanup()
    def call(self,path,data=None,token=None,origin=None):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        if origin:headers['Origin']=origin
        request=Request(self.url+path,data=json.dumps(data).encode() if data is not None else None,headers=headers)
        try:
            with urlopen(request,timeout=30) as r:
                raw=r.read();return r.status,raw,json.loads(raw) if r.headers.get_content_type()=='application/json' else None
        except HTTPError as e:return e.code,e.read(),None
    def login(self,user):return self.call('/api/login',{'user':user})[2]['token']
    def test_access_and_real_transfer(self):
        self.assertEqual(self.call('/api/state')[0],401)
        bob,alice,raka=(self.login(u) for u in ('bob','alice','raka'))
        raw=bytes(range(256))*31+b'\0\0FINAL'
        status,_,response=self.call('/api/send',{'recipient':'alice','note':'Biner dan Unicode 🔐','files':[{'name':'berkas.bin','mime':'application/octet-stream','data':base64.b64encode(raw).decode()}]},bob)
        self.assertEqual(status,201);fid=response['ids'][0]
        self.assertEqual(self.call('/api/files/'+fid,token=raka)[0],404)
        self.assertEqual(self.call('/api/files/'+fid,token=alice)[2]['note'],'Biner dan Unicode 🔐')
        self.assertEqual(self.call('/api/files/'+fid+'/download',token=alice)[1],raw)
        self.assertEqual(self.call('/api/state',token=bob)[2]['records'][0]['status'],'Sudah dibuka')
        with server.connect() as db:
            row=db.execute('SELECT cipher FROM files WHERE id=?',(fid,)).fetchone();cipher=bytearray(row['cipher']);cipher[-1]^=1
            db.execute('UPDATE files SET cipher=? WHERE id=?',(bytes(cipher),fid))
        self.assertEqual(self.call('/api/files/'+fid+'/download',token=alice)[0],400)
    def test_validation_and_no_private_files_served(self):
        token=self.login('bob')
        self.assertEqual(self.call('/data/filedrop.sqlite3')[0],404)
        self.assertEqual(self.call('/crypto_core.py')[0],404)
        self.assertEqual(self.call('/api/login',{'user':'bob'},origin='https://example.invalid')[0],403)
        for target,entries in [('bob',[]),('alice',[]),('alice',[{'name':'../bad.txt','data':''}])]:
            self.assertEqual(self.call('/api/send',{'recipient':target,'files':entries},token)[0],400)

if __name__=='__main__':unittest.main(verbosity=2)
