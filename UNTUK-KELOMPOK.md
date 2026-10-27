# Untuk anggota kelompok

Semua kode aplikasi, laporan, tampilan, dan pengujian ada di repositori ini.

1. Unduh repositori atau clone.
2. Jalankan `JALANKAN.bat` (memerlukan Python 3.10+), atau `python server.py --open`.
3. Kirim sebagai Bob kepada Alice, lalu ganti akun ke Alice untuk menerima dan mengunduh.
4. Data awal memang kosong. Coba file contoh atau pilih file sendiri.

Database dan kunci tidak perlu disalin. `server.py:init_db()` membuat database serta kunci akun secara otomatis saat pertama dijalankan. Setiap komputer mempunyai data dan kuncinya sendiri. Akun pada dua tab di komputer yang sama dapat saling mengirim melalui server lokal yang sama.

Implementasi matematika berada di `crypto_core.py`: Diffie-Hellman, ElGamal, square-and-multiply, Euclid diperluas, SHA-256, dan HMAC ditulis mandiri. Satu-satunya impor pada modul tersebut adalah `secrets`, khusus untuk sumber angka acak. Tidak ada library enkripsi/dekripsi siap pakai. `hashlib`/`hmac` di folder tes hanya menjadi pembanding hasil, tidak digunakan aplikasi.

Laporan PDF sudah disertakan dan menyediakan kolom identitas yang bisa diisi pada halaman pertama. Jangan lupa isi kelompok, nama, dan NRP sebelum mengumpulkan ZIP.

Catatan: ini aplikasi tugas lokal. Belum merupakan layanan internet untuk mengirim antar komputer dan bukan sistem keamanan produksi. Baca README untuk cakupan lengkap.
