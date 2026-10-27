"""Oracle hashlib/hmac hanya untuk pengujian, tidak digunakan aplikasi."""
import hashlib
import hmac
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import crypto_core as c
import server

class CryptoTests(unittest.TestCase):
    def test_parameters(self):
        self.assertTrue(c.validate_parameters())
    def test_diffie_hellman_ppt_slide11(self):
        d=c.diffie_hellman(251,6,124,158)
        self.assertEqual((d['A'],d['B'],d['sender_key'],d['receiver_key']),(209,197,79,79))
    def test_elgamal_ppt_slides15_20(self):
        x,y=c.keygen(2273,3,243)
        self.assertEqual(y,461)
        self.assertEqual(c.encrypt_number(700,y,1463,2273,3),(1439,74))
        self.assertEqual(c.encrypt_number(1114,y,2001,2273,3),(1220,1682))
        self.assertEqual(c.decrypt_number(1439,74,x,2273),700)
        self.assertEqual(c.decrypt_number(1220,1682,x,2273),1114)
        self.assertEqual(c.inverse(c.mod_pow(1439,x,2273),2273),1791)
    def test_modpow_independent_oracle(self):
        for b in range(20):
            for e in range(30):
                self.assertEqual(c.mod_pow(b,e,251),(b**e)%251)
    def test_binary_roundtrip_all_bytes_and_zero_padding(self):
        x,y=c.keygen()
        for data in [b'',b'\0',b'\0\0\0hello\0',bytes(range(256))*4,b'\xff'*15,'Halo 🔐 日本語'.encode(),b'0'*7,b'0'*8]:
            cipher=c.encrypt_bytes(data,y)
            self.assertEqual(c.decrypt_bytes(cipher,len(data),x),data)
    def test_encryption_is_randomized(self):
        _,y=c.keygen()
        self.assertNotEqual(c.encrypt_bytes(b'same message',y),c.encrypt_bytes(b'same message',y))
    def test_sha256_standard_oracle(self):
        for data in [b'',b'abc',b'a'*55,b'a'*56,b'a'*63,b'a'*64,b'a'*65,bytes(range(256))*5]:
            self.assertEqual(c.sha256(data),hashlib.sha256(data).digest())
    def test_hmac_standard_oracle(self):
        for key in [b'',b'key',bytes(range(100))]:
            for data in [b'',b'message',b'a'*500]:
                self.assertEqual(c.hmac_sha256(key,data),hmac.new(key,data,hashlib.sha256).digest())
    def test_invalid_cipher_and_inverse(self):
        with self.assertRaises(ValueError):c.inverse(0,c.P)
        with self.assertRaises(ValueError):c.decrypt_bytes(b'bad',100,243)
        with self.assertRaises(ValueError):c.decrypt_number(0,1,243)
    def test_file_record_persistence_and_tamper_rejection(self):
        old=server.DATA
        with tempfile.TemporaryDirectory() as temp:
            server.DATA=Path(temp);server.init_db()
            raw=b'\x00\xffFILE-SECURE-DROP-NO-PLAINTEXT\x00'+bytes(range(256))
            record=server.make_record('bob','alice','hasil.bin','application/octet-stream','Pesan privat 🔐',raw)
            server.insert_records([record])
            with server.connect() as db:
                row=db.execute('SELECT * FROM files WHERE id=?',(record[0],)).fetchone()
            result,header=server.receive_record(row)
            self.assertEqual(result,raw);self.assertEqual(header['note'],'Pesan privat 🔐')
            self.assertNotIn(raw,bytes(row['cipher']))
            changed=dict(row);cipher=bytearray(row['cipher']);cipher[12]^=1;changed['cipher']=bytes(cipher)
            with self.assertRaisesRegex(ValueError,'berubah|rusak'):server.receive_record(changed)
            changed=dict(row);changed['name']='diubah.bin'
            with self.assertRaises(ValueError):server.receive_record(changed)
            self.assertEqual(server.state_for('alice')['records'][0]['direction'],'inbox')
            self.assertEqual(server.state_for('bob')['records'][0]['direction'],'sent')
            self.assertEqual(server.state_for('raka')['records'],[])
        server.DATA=old

if __name__=='__main__':unittest.main(verbosity=2)
