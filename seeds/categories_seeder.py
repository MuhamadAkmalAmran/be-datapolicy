from flask_seeder import Seeder
from models import Category
from datetime import datetime

class CategorySeeder(Seeder):
    """Seeder class for Category table"""

    def run(self):
        categories = [
            (1, 'Indeks Pembangunan Manusia', '2025-01-07 10:59:35'),
            (2, 'Jumlah Penduduk Miskin', '2025-01-07 10:59:35'),
            (3, 'Prevalensi Stunting', '2025-01-07 10:59:53'),
            (4, 'APBD', '2025-01-23 07:38:29'),
            (5, 'Persentase Penduduk Miskin', '2025-03-07 05:26:03'),
            (6, 'Umur Harapan Hidup Saat Lahir', '2025-03-08 09:18:58'),
            (7, 'Tingkat Partisipasi Angkatan Kerja', '2025-03-15 11:59:27'),
            (8, 'Jumlah Angkatan Kerja', '2025-03-22 09:06:16'),
            (9, 'PDRB Pertanian, Kehutanan, dan Perikanan', '2025-03-22 10:16:58'),
            (10, 'Indeks Gini', '2025-02-26 21:41:48'),
            (11, 'Partisipasi Sekolah', '2025-06-30 18:26:07'),
            (28, 'APBD - Pendapatan Daerah', '2025-08-23 17:02:28'),
            (29, 'APBD - Pendapatan Daerah - PAD', '2025-08-23 17:02:28'),
            (30, 'APBD - Pendapatan Daerah - TKDD', '2025-08-23 17:02:28'),
            (31, 'APBD - Pendapatan Daerah - Pendapatan Lainnya', '2025-08-23 17:02:28'),
            (32, 'APBD - Pendapatan Daerah - PAD - Pajak Daerah', '2025-08-23 17:02:28'),
            (33, 'APBD - Pendapatan Daerah - PAD - Retribusi Daerah', '2025-08-23 17:02:28'),
            (34, 'APBD - Pendapatan Daerah - PAD - Hasil Pengelolaan Kekayaan Daerah yang Dipisahkan', '2025-08-23 17:02:28'),
            (35, 'APBD - Pendapatan Daerah - PAD - Lain-Lain PAD yang Sah', '2025-08-23 17:02:28'),
            (36, 'APBD - Pendapatan Daerah - TKDD - Pendapatan Transfer Pemerintah Pusat', '2025-08-23 17:02:28'),
            (37, 'APBD - Pendapatan Daerah - TKDD - Pendapatan Transfer Antar Daerah', '2025-08-23 17:02:28'),
            (38, 'APBD - Pendapatan Daerah - Pendapatan Lainnya - Pendapatan Hibah', '2025-08-23 17:02:28'),
            (39, 'APBD - Pendapatan Daerah - Pendapatan Lainnya - Dana Darurat', '2025-08-23 17:02:28'),
            (40, 'APBD - Pendapatan Daerah - Pendapatan Lainnya - Lain-lain Pendapatan Sesuai dengan Ketentuan Peraturan Perundang-Undangan', '2025-08-23 17:02:28'),
            (41, 'APBD - Belanja Daerah', '2025-08-30 10:26:02'),
            (42, 'APBD - Belanja Daerah - Belanja Pegawai', '2025-08-30 10:26:02'),
            (43, 'APBD - Belanja Daerah - Belanja Barang dan Jasa', '2025-08-30 10:26:02'),
            (44, 'APBD - Belanja Daerah - Belanja Modal', '2025-08-30 10:26:02'),
            (45, 'APBD - Belanja Daerah - Belanja Lainnya', '2025-08-30 10:26:02'),
            (46, 'APBD - Belanja Daerah - Belanja Lainnya - Belanja Bantuan Keuangan', '2025-08-30 10:26:02'),
            (47, 'APBD - Belanja Daerah - Belanja Lainnya - Belanja Subsidi', '2025-08-30 10:26:02'),
            (48, 'APBD - Belanja Daerah - Belanja Lainnya - Belanja Hibah', '2025-08-30 10:26:02'),
            (49, 'APBD - Belanja Daerah - Belanja Lainnya - Belanja Bantuan Sosial', '2025-08-30 10:26:02'),
            (50, 'APBD - Belanja Daerah - Belanja Lainnya - Belanja Tidak Terduga', '2025-08-30 10:26:02'),
            (60, 'APBD - Pembiayaan Daerah', '2025-08-30 13:22:56'),
            (61, 'APBD - Pembiayaan Daerah - Penerimaan Pembiayaan Daerah', '2025-08-30 13:22:56'),
            (62, 'APBD - Pembiayaan Daerah - Penerimaan Pembiayaan Daerah - Sisa Lebih Perhitungan Anggaran Tahun Sebelumnya', '2025-08-30 13:22:56'),
            (63, 'APBD - Pembiayaan Daerah - Penerimaan Pembiayaan Daerah - Penerimaan Kembali Pemberian Pinjaman Daerah', '2025-08-30 13:22:56'),
            (64, 'APBD - Pembiayaan Daerah - Pengeluaran Pembiayaan Daerah', '2025-08-30 13:22:56'),
            (65, 'APBD - Pembiayaan Daerah - Pengeluaran Pembiayaan Daerah - Penyertaan Modal Daerah', '2025-08-30 13:22:56'),
            (66, 'Indeks Pemenuhan Hak Anak', '2025-09-11 20:11:45'),
        ]

        for id, name, created_at in categories:
            if not Category.query.get(id):
                category = Category(
                    id=id,
                    name=name,
                    created_at=datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                )
                self.db.session.add(category)

        self.db.session.commit()
        print("✅ CategorySeeder finished inserting categories.")
