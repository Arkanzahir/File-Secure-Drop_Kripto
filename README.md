# File Secure Drop

Aplikasi lokal pengiriman file untuk tugas Diffie-Hellman dan ElGamal. HTML, CSS, JavaScript, dan Python standard library. Tidak ada pip/npm, framework, CDN, atau library kriptografi.

## Menjalankan

1. Clone repositori ini atau unduh melalui Code > Download ZIP, lalu ekstrak.
2. Pastikan Python 3.10+ terpasang.
3. Klik **JALANKAN.bat**. Biarkan jendela server terbuka.
4. Browser membuka **http://127.0.0.1:8772**.

Alternatif: `python server.py --open`. Jika port terpakai, jalankan `python server.py --port 8780 --open`.

## Demo cepat

1. Mulai sebagai **Bob**. Pilih file sendiri atau **Coba file contoh**.
2. Pilih penerima **Alice**, tambahkan pesan opsional, klik **Kirim file**.
3. Klik **Akun: Bob** di kanan atas, lalu pilih **Alice**.
4. Buka **Kotak masuk**, pilih kiriman, klik **Unduh file**.
5. Bandingkan file hasil unduhan dengan aslinya. Isinya identik.
6. Kembali ke Bob untuk melihat status **Sudah dibuka**.

Bisa memakai dua tab atau dua browser pada komputer yang sama dengan akun berbeda. Akun disimpan per tab. Daftar kiriman diperbarui otomatis setiap 6 detik. Kiriman dan kunci disimpan di `data/filedrop.sqlite3`, sehingga tetap ada setelah reload/restart. Database dan kunci otomatis dibuat di komputer masing-masing saat pertama menjalankan aplikasi; keduanya tidak diunggah ke GitHub.

Maksimal 5 file, total **1 MB** per kiriman. Batas ini menjaga kecepatan ElGamal langsung per blok, bukan enkripsi simetri pengganti. Semua jenis file/biner didukung, termasuk file kosong, Unicode, dan byte nol.

## Cara kerja untuk pemeriksaan kode

Satu studi kasus: Bob mengirim dokumen kepada Alice.

1. `crypto_core.py:keygen`: pasangan kunci ElGamal tiap akun, y = g^x mod p.
2. `diffie_hellman`: a dan b acak baru tiap file, A dan B publik, K dihitung independen oleh kedua pihak.
3. `integrity_key`: SHA-256 mandiri mengolah K DH menjadi kunci HMAC.
4. `encrypt_bytes`: seluruh isi file dan catatan dibagi per 7 byte. Setiap blok memakai k acak berbeda. c1 = g^k mod p, c2 = m*y^k mod p.
5. `hmac_sha256`: melindungi metadata dan ciphertext memakai K DH. Jadi hasil DH benar-benar dipakai.
6. `server.py:receive_record`: penerima menghitung K dari A^b, memverifikasi HMAC, kemudian mendekripsi ElGamal dengan x penerima.
7. `decrypt_number`: menghitung invers dengan Euclid diperluas. Ukuran blok menjaga byte nol dan blok terakhir.
8. SHA-256 isi file membandingkan hasil pulih dengan file asli sebelum unduhan.

Tidak ada kunci, rumus, atau ciphertext yang ditampilkan di antarmuka. Fungsi dan komentar di kode menjelaskan tiap tahapan. HMAC/SHA-256 merupakan tambahan integritas, bukan pengganti ElGamal. SHA-256 dan HMAC juga ditulis mandiri. Modul `secrets` bawaan Python hanya menjadi sumber angka acak.

Parameter aplikasi: p = 2^61 - 1 = 2305843009213693951, g = 37. Keprimaan diverifikasi dengan Lucas-Lehmer. Basis diverifikasi lewat faktorisasi p-1. Parameter lebih besar dari contoh PPT agar setiap blok dapat menyimpan 7 byte, tetapi tetap kecil untuk demo. Contoh asli PPT diuji terpisah: DH K=79 dan ElGamal HALO menjadi (1439,74), (1220,1682).

## Laporan

[Laporan program](laporan/Laporan-File-Secure-Drop.pdf) memuat studi kasus, penjelasan algoritma, hasil validasi, dan petunjuk penggunaan. Isi kelompok, nama, dan NRP pada halaman pertama sebelum dikumpulkan.

## Cakupan

Ini simulasi tugas lokal, bukan layanan produksi. Akun dipilih tanpa password untuk demo. Server mengelola kedua sisi serta kunci privat, sehingga ini bukan enkripsi end-to-end antar perangkat. Server hanya mendengarkan 127.0.0.1. HTTP lokal bukan TLS, parameter 61 bit tidak cocok untuk keamanan nyata, dan DH tanpa autentikasi identitas tidak mengatasi MITM. Tidak ada klaim keamanan produksi.

## Sumber

- PPT Pertemuan ke-9_El Gamal dan Diffie-Hellman, slide 8-20.
- Menezes, van Oorschot, Vanstone. Handbook of Applied Cryptography, §8.4 dan §12.6: https://cacr.uwaterloo.ca/hac/about/chap8.pdf dan https://cacr.uwaterloo.ca/hac/about/chap12.pdf
- SHA-256: FIPS 180-4, https://csrc.nist.gov/pubs/fips/180-4/upd1/final
- HMAC: RFC 2104, https://www.rfc-editor.org/rfc/rfc2104
