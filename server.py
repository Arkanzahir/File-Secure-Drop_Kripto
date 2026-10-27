"""Server lokal File Secure Drop. Hanya Python standard library.
Jalankan: python server.py --open
"""
import argparse
import base64
import json
import mimetypes
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, quote
import webbrowser
from crypto_core import (P,G,keygen,diffie_hellman,encrypt_bytes,decrypt_bytes,
                         mod_pow,integrity_key,hmac_sha256,same_tag,sha256,validate_parameters)

ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('FILEDROP_DATA_DIR',str(ROOT/'data')))
MAX_TOTAL=1024*1024
USERS=[('bob','Bob','B','sage'),('alice','Alice','A','sage'),('nadia','Nadia','N','clay'),('raka','Raka','R','blue')]
TOKENS={}
TOKEN_LOCK=threading.Lock()

class ClosingConnection(sqlite3.Connection):
    def __exit__(self,*args):
        try:
            return super().__exit__(*args)
        finally:
            self.close()

def connect():
    db=sqlite3.connect(DATA/'filedrop.sqlite3',timeout=30,factory=ClosingConnection)
    db.row_factory=sqlite3.Row
    return db

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')

def init_db():
    validate_parameters()
    DATA.mkdir(parents=True,exist_ok=True)
    with connect() as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,name TEXT,private TEXT,public TEXT)')
        db.execute('''CREATE TABLE IF NOT EXISTS files(
          id TEXT PRIMARY KEY,sender TEXT,recipient TEXT,name TEXT,size INTEGER,date TEXT,
          opened INTEGER DEFAULT 0,aad BLOB,cipher BLOB,tag BLOB,dh_a_public TEXT,
          dh_b_private TEXT,dh_b_public TEXT,payload_size INTEGER)''')
        for uid,name,_,_ in USERS:
            if not db.execute('SELECT id FROM users WHERE id=?',(uid,)).fetchone():
                x,y=keygen()
                db.execute('INSERT INTO users VALUES(?,?,?,?)',(uid,name,str(x),str(y)))

def make_record(sender,recipient,name,mime,note,data):
    """Satu studi kasus: DH menyepakati kunci integritas; ElGamal menyandi file."""
    with connect() as db:
        receiver=db.execute('SELECT public FROM users WHERE id=?',(recipient,)).fetchone()
    if not receiver:
        raise ValueError('Penerima tidak ditemukan.')
    session=diffie_hellman()
    # Header (pesan dan jenis file) ikut dienkripsi, diikuti seluruh byte file.
    header=canonical({'mime':mime,'note':note})
    payload=len(header).to_bytes(4,'big')+header+data
    cipher=encrypt_bytes(payload,int(receiver['public']))
    fid=secrets.token_hex(12)
    date=datetime.now(timezone.utc).isoformat()
    metadata={'version':1,'id':fid,'sender':sender,'recipient':recipient,'name':name,
              'size':len(data),'date':date,'digest':sha256(data).hex(),
              'dh_A':str(session['A']),'dh_B':str(session['B']),'payload_size':len(payload)}
    aad=canonical(metadata)
    # HMAC memakai K DH pihak pengirim. Penerima menghitung K sendiri saat membuka.
    tag=hmac_sha256(integrity_key(session['sender_key']),aad+cipher)
    return (fid,sender,recipient,name,len(data),date,0,aad,cipher,tag,
            str(session['A']),str(session['b']),str(session['B']),len(payload))

def receive_record(row):
    """Verifikasi integritas sebelum dekripsi. Tidak pernah mengirim kunci ke UI."""
    with connect() as db:
        receiver=db.execute('SELECT private FROM users WHERE id=?',(row['recipient'],)).fetchone()
    shared=mod_pow(int(row['dh_a_public']),int(row['dh_b_private']),P)
    expected=hmac_sha256(integrity_key(shared),bytes(row['aad'])+bytes(row['cipher']))
    if not same_tag(expected,bytes(row['tag'])):
        raise ValueError('Kiriman berubah atau rusak. File tidak dapat dibuka.')
    metadata=json.loads(bytes(row['aad']))
    # Metadata database harus tetap sama dengan metadata yang dilindungi HMAC.
    for field in ('id','sender','recipient','name','size','date','payload_size'):
        if metadata[field]!=row[field]:
            raise ValueError('Informasi kiriman tidak cocok.')
    if metadata['dh_A']!=row['dh_a_public'] or metadata['dh_B']!=row['dh_b_public']:
        raise ValueError('Informasi sesi tidak cocok.')
    payload=decrypt_bytes(bytes(row['cipher']),row['payload_size'],int(receiver['private']))
    if len(payload)<4:
        raise ValueError('Isi kiriman tidak valid.')
    header_size=int.from_bytes(payload[:4],'big')
    if header_size>4096 or 4+header_size>len(payload):
        raise ValueError('Header file tidak valid.')
    header=json.loads(payload[4:4+header_size])
    data=payload[4+header_size:]
    if len(data)!=row['size'] or sha256(data).hex()!=metadata['digest']:
        raise ValueError('Hasil pemulihan file tidak cocok.')
    return data,header

def insert_records(records):
    with connect() as db:
        db.executemany('INSERT INTO files VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',records)

def state_for(uid):
    with connect() as db:
        rows=db.execute('SELECT id,sender,recipient,name,size,date,opened FROM files WHERE sender=? OR recipient=? ORDER BY date DESC',(uid,uid)).fetchall()
    result=[]
    for r in rows:
        outgoing=r['sender']==uid
        result.append({'id':r['id'],'name':r['name'],'size':r['size'],'person':r['recipient'] if outgoing else r['sender'],
          'date':r['date'],'status':('Sudah dibuka' if r['opened'] else 'Terkirim') if outgoing else ('Sudah dibuka' if r['opened'] else 'Baru'),
          'direction':'sent' if outgoing else 'inbox'})
    return {'current':uid,'users':[{'id':u,'name':n,'initials':i,'color':c} for u,n,i,c in USERS],
            'records':result,'maxBytes':MAX_TOTAL}

class Handler(BaseHTTPRequestHandler):
    server_version='FileSecureDrop/1.0'
    def log_message(self,fmt,*args):
        # Jangan mencatat token, isi dokumen, atau kunci.
        print('%s %s'%(self.command,urlparse(self.path).path),flush=True)
    def reply(self,status,value):
        data=json.dumps(value,ensure_ascii=False).encode('utf-8')
        self.send_response(status);self.common_headers()
        self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(data)))
        self.end_headers();self.wfile.write(data)
    def common_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Cache-Control','no-store')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
    def user(self):
        token=self.headers.get('Authorization','').removeprefix('Bearer ')
        with TOKEN_LOCK:
            entry=TOKENS.get(token)
        if not entry or time.time()-entry[1]>43200:
            raise PermissionError('Pilih akun untuk melanjutkan.')
        return entry[0]
    def body(self):
        length=int(self.headers.get('Content-Length','0'))
        if length<0 or length>1600000:
            raise ValueError('Ukuran permintaan melebihi batas 1 MB file.')
        return json.loads(self.rfile.read(length))
    def record(self,fid,uid):
        with connect() as db:
            row=db.execute('SELECT * FROM files WHERE id=? AND (sender=? OR recipient=?)',(fid,uid,uid)).fetchone()
        if not row:
            raise FileNotFoundError('File tidak ditemukan untuk akun ini.')
        return row
    def do_GET(self):
        path=urlparse(self.path).path
        try:
            if path=='/api/state':
                return self.reply(200,state_for(self.user()))
            if path.startswith('/api/files/'):
                uid=self.user(); parts=path.split('/');fid=parts[3]
                row=self.record(fid,uid)
                data,header=receive_record(row)
                if row['recipient']==uid:
                    with connect() as db:
                        db.execute('UPDATE files SET opened=1 WHERE id=?',(fid,))
                if path.endswith('/download'):
                    self.send_response(200);self.common_headers()
                    self.send_header('Content-Type','application/octet-stream')
                    self.send_header('Content-Disposition',"attachment; filename*=UTF-8''"+quote(row['name'],safe=''))
                    self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
                    return
                return self.reply(200,{'id':fid,'note':header['note'],'mime':header['mime'],'verified':True})
            allowed={'/':'index.html','/index.html':'index.html','/styles.css':'styles.css','/app.js':'app.js','/favicon.ico':None}
            if path not in allowed or allowed[path] is None:
                return self.reply(404,{'error':'Halaman tidak ditemukan.'})
            file=ROOT/allowed[path];data=file.read_bytes()
            self.send_response(200);self.common_headers()
            mime=mimetypes.guess_type(file.name)[0] or 'application/octet-stream'
            self.send_header('Content-Type',mime+'; charset=utf-8');self.send_header('Content-Length',str(len(data)))
            self.end_headers();self.wfile.write(data)
        except PermissionError as e:self.reply(401,{'error':str(e)})
        except FileNotFoundError as e:self.reply(404,{'error':str(e)})
        except (ValueError,KeyError,TypeError,OverflowError) as e:self.reply(400,{'error':str(e)})
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:
            print('Error:',type(e).__name__,str(e),flush=True)
            self.reply(500,{'error':'Kiriman belum dapat diproses. Silakan coba lagi.'})
    def do_POST(self):
        try:
            # API lokal tidak menerima mutasi dari halaman asal lain.
            origin=self.headers.get('Origin')
            host=self.headers.get('Host','')
            if origin and origin!='http://'+host:
                return self.reply(403,{'error':'Asal permintaan tidak diizinkan.'})
            path=urlparse(self.path).path
            if path=='/api/login':
                data=self.body();uid=data.get('user')
                if uid not in [u[0] for u in USERS]:
                    raise ValueError('Akun tidak ditemukan.')
                token=secrets.token_urlsafe(32)
                with TOKEN_LOCK:TOKENS[token]=(uid,time.time())
                return self.reply(200,{'token':token,**state_for(uid)})
            uid=self.user()
            if path=='/api/send':
                data=self.body();target=data.get('recipient');entries=data.get('files');note=data.get('note','')
                if target==uid or target not in [u[0] for u in USERS]:
                    raise ValueError('Pilih penerima lain yang valid.')
                if not isinstance(note,str) or len(note)>200:
                    raise ValueError('Pesan maksimal 200 karakter.')
                if not isinstance(entries,list) or not 1<=len(entries)<=5:
                    raise ValueError('Pilih 1 sampai 5 file.')
                decoded=[];total=0
                for f in entries:
                    name=f.get('name','');mime=f.get('mime','application/octet-stream')
                    if not isinstance(name,str) or not name or len(name)>180 or any(ord(c)<32 for c in name) or '/' in name or '\\' in name:
                        raise ValueError('Nama file tidak valid (maks. 180 karakter).')
                    if not isinstance(mime,str) or len(mime)>150:
                        raise ValueError('Jenis file tidak valid.')
                    raw=base64.b64decode(f.get('data',''),validate=True)
                    total+=len(raw)
                    if total>MAX_TOTAL:raise ValueError('Total file maksimal 1 MB per kiriman.')
                    decoded.append((name,mime,raw))
                # Semua file diproses sebelum transaksi sehingga tidak ada kiriman parsial.
                created=[make_record(uid,target,name,mime,note,raw) for name,mime,raw in decoded]
                insert_records(created)
                return self.reply(201,{'ids':[r[0] for r in created],**state_for(uid)})
            return self.reply(404,{'error':'Aksi tidak ditemukan.'})
        except PermissionError as e:self.reply(401,{'error':str(e)})
        except (ValueError,KeyError,TypeError,OverflowError) as e:self.reply(400,{'error':str(e)})
        except (BrokenPipeError,ConnectionResetError):pass
        except Exception as e:
            print('Error:',type(e).__name__,str(e),flush=True)
            self.reply(500,{'error':'Pengiriman gagal. Tidak ada file yang disimpan sebagian.'})

def main():
    parser=argparse.ArgumentParser(description='File Secure Drop - aplikasi lokal tugas kriptografi')
    parser.add_argument('--port',type=int,default=8772);parser.add_argument('--open',action='store_true')
    args=parser.parse_args();init_db()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    url=f'http://127.0.0.1:{args.port}'
    print(f'File Secure Drop aktif: {url}\nTekan Ctrl+C untuk berhenti.',flush=True)
    if args.open:webbrowser.open(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()

if __name__=='__main__':main()
