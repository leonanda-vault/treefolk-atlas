# Laporan Metodologi Ilmiah & Integrasi Alur Kerja
## Adaptasi Treefolk Atlas (i-Tree SEA) untuk Wilayah Tropis Asia Tenggara

> **Referensi Dokumen:** ATLAS-METHODOLOGY-v0.5-ID  
> **Tanggal:** Mei 2026  
> **Target Pembaca:** Arsitek Lanskap, Rimbawan Perkotaan, Surveyor, dan Konsultan Lingkungan  
> **Dokumentasi Repositori:** [methodology_id.md](file:///d:/Leonanda's%20Professional%20Vault/Projects/itree-sea/docs/methodology_id.md)

---

## 1. Ringkasan Eksekutif

**Treefolk Atlas (i-Tree SEA)** adalah platform evaluasi kehutanan perkotaan bersumber terbuka (open-source) yang terspesialisasi. Platform ini mengadaptasi dan memperluas metodologi i-Tree Eco dari USDA Forest Service agar sesuai dengan kondisi iklim, taksonomi, dan struktural yang unik di wilayah tropis khatulistiwa Asia Tenggara (zona iklim Köppen *Af* dan *Am*).

Dengan mengintegrasikan berat jenis kayu spesifik per spesies, model tinggi-diameter tropis (regresi Weibull), persamaan khusus monokotil (palem), dan modifikator kanopi berbasis morfologi, alat ini menyediakan mesin kalkulasi yang sangat terlokalisasi bagi arsitek lanskap dan surveyor untuk mengukur manfaat ekologis dari infrastruktur hijau perkotaan. Platform ini menerjemahkan inventarisasi lapangan atau tata letak CAD/GIS menjadi metrik lingkungan yang dapat diaudit, termasuk penyimpanan karbon, sekuestrasi karbon bruto, produksi oksigen, penyerapan polusi udara melalui deposisi kering, dan pengurangan limpasan air hujan (stormwater).

---

## 2. Metodologi Ilmiah Inti & Dasar Matematika

Berbeda dengan mesin kalkulasi iklim sedang (temperate) yang mengandalkan kategorisasi sederhana pohon berdaun lebar (hardwood) atau jarum (conifer), Treefolk Atlas menggunakan parameter lokal dan formula biologis khusus.

### 2.1 Perhitungan Biomassa di Atas Tanah (Aboveground Biomass - AGB)

#### Untuk Pohon Dikotil (Spesies Berdaun Lebar & Jarum Standar)
Mesin ini menerapkan model alometrik pantropis oleh **Chave et al. (2014)** sebagai basis untuk biomassa di atas tanah:

$$\text{AGB}_{\text{base}} = 0.0673 \times (\rho \times D^2 \times H)^{0.976}$$

Dimana:
*   $\text{AGB}_{\text{base}}$ adalah biomassa kering di atas tanah (kg).
*   $\rho$ adalah berat jenis kayu dasar spesifik spesies (g/cm³), bersumber dari **Global Wood Density Database (Chave 2009, Zanne 2009)**.
*   $D$ is Diameter at Breast Height (DBH, cm) yang diukur pada ketinggian 1,3 m di atas tanah.
*   $H$ adalah tinggi total pohon (m).

Untuk mengakomodasi perbedaan arsitektur pohon perkotaan yang tumbuh di ruang terbuka, mesin kalkulasi membagi biomassa menjadi komponen kayu (woody) dan dedaunan (foliage):

1.  **Ekstraksi Komponen Kayu:**
    $$\text{Woody}_{\text{base}} = \text{AGB}_{\text{base}} \times (1 - \text{DEFAULT\_FOLIAGE\_FRACTION})$$
    *(dimana $\text{DEFAULT\_FOLIAGE\_FRACTION} = 0.05$ atau $5\%$)*

2.  **Koreksi Morfologi untuk Struktur:**
    $$\text{Woody}_{\text{adjusted}} = \text{Woody}_{\text{base}} \times f_{\text{trunk}} \times f_{\text{crown}}$$
    *   **Pengali Bentuk Batang ($f_{\text{trunk}}$):** Batang tunggal standar (`1.0`), Pangkal berbanir (misalnya, *Ficus*, *Samanea* = `1.15`), dan Struktur bercabang banyak (misalnya, rumpun *Dypsis lutescens* = `0.85`).
    *   **Pengali Bentuk Tajuk ($f_{\text{crown}}$):** Kolumnar/Pilar (`0.80`), Konikal/Kerucut (`0.90`), Bulat/Bola (`1.00`), Melebar/Payung (`1.15`).

3.  **Perhitungan Komponen Dedaunan:**
    Alih-alih menghitung dedaunan sebagai fraksi statis, mesin memodelkan biomassa daun secara dinamis dari geometri tajuk dan kerapatan daun:
    $$\text{Foliage} = \text{Crown Area} \times \text{LAI}_{\text{species}} \times \text{SLW}$$
    *   **Luas Tajuk / Crown Area (m²):** Diturunkan dari Lebar Tajuk ($CW$), di mana $CW = 0.6 + (k_{cw} \times DBH)$ dengan batas maksimum 20 m.
    *   **Modifikator Tajuk ($k_{cw}$):** Faktor arsitektur kanopi spesifik (Kolumnar = `0.08`, Standar/Oval = `0.15`, Melebar/Payung = `0.25 - 0.30`).
    *   **Indeks Area Daun / Leaf Area Index ($\text{LAI}_{\text{species}}$):** Pengali kerapatan dedaunan spesifik spesies (bawaan = `5.0`).
    *   **Berat Daun Spesifik / Specific Leaf Weight (SLW, kg/m²):** Diskalakan berdasarkan kelas morfologi daun (Daun Tunggal = `0.12`, Daun Majemuk = `0.09`, Daun Jarum = `0.22`, Daun Kipas Palem = `0.32`).

$$\text{AGB}_{\text{final}} = \text{Woody}_{\text{adjusted}} + \text{Foliage}$$

Untuk mengakomodasi arsitektur pohon yang tumbuh di ruang terbuka di lingkungan perkotaan, mesin menerapkan faktor penyesuaian perkotaan dinamis:
$$\text{AGB}_{\text{final\_urban}} = \text{AGB}_{\text{final}} \times f_{\text{urban}}$$
Di mana $f_{\text{urban}}$ dihitung berdasarkan Crown Light Exposure (CLE, 0 hingga 5):
$$f_{\text{urban}} = \max\left(0.80, \min\left(1.00, 0.80 + 0.04 \times (5 - CLE)\right)\right)$$

#### Untuk Pohon Monokotil (Palem)
Model alometrik dikotil standar cenderung menaksir terlalu tinggi (overestimate) biomassa palem karena perbedaan mekanika struktural (batang silindris tanpa pengecilan diameter ke atas, tidak adanya pertumbuhan lateral sekunder kambium, dan rasio air-ke-massa kering yang tinggi). Treefolk Atlas menerapkan **Model Batang Silindris** khusus:

$$\text{AGB}_{\text{palm}} = 0.07854 \times \rho \times D^2 \times H$$

*   *Penurunan Rumus:* Volume silinder adalah $V = \frac{\pi}{4} \times (\frac{D}{100})^2 \times H = \frac{\pi}{40000} \times D^2 \times H$ (m³). Mengonversi volume menjadi massa kering menggunakan berat jenis kayu kering ($\rho \times 1000$ kg/m³) menghasilkan:
    $$\text{AGB}_{\text{palm}} = \left(\frac{\pi}{40000} \times 1000\right) \times \rho \times D^2 \times H \approx 0.07854 \times \rho \times D^2 \times H$$
*   *Kalibrasi Taksonomi:* Fraksi karbon dasar disesuaikan ke bawah menjadi **0.41** (dibandingkan dengan 0.50 pada dikotil) untuk mencerminkan kandungan lignin yang lebih rendah pada berkas pengangkut monokotil (IPCC 2006).

### 2.2 Model Hidrologi Stormwater: Neraca Air Kanopi Harian

Alih-alih menggunakan proksi kejadian tahunan yang disederhanakan, mesin menerapkan model neraca air kanopi basah harian yang digerakkan oleh evaporasi daun potensial Penman-Monteith untuk mengurangi kesalahan prediksi:

1. **Laju Evaporasi ($E$, mm/hari):** Diestimasi dari suhu, kecepatan angin, dan kelembaban relatif menggunakan persamaan Penman:
   $$E = \frac{\Delta \cdot R_n + \gamma \cdot f(u) \cdot (e_s - e_a)}{\Delta + \gamma}$$
   Di mana:
   *   $\Delta$ adalah kemiringan kurva tekanan uap jenuh.
   *   $\gamma$ adalah konstanta psikrometrik ($0.066$).
   *   $R_n$ adalah radiasi matahari bersih ($2.5\text{ MJ/m}^2/\text{hari}$).
   *   $f(u)$ adalah fungsi angin: $f(u) = 2.626 \cdot (1.0 + 0.54 \cdot u)$, di mana $u$ adalah kecepatan angin ($m/s$).
   *   $e_s - e_a$ adalah defisit tekanan uap.

2. **Pelacakan Penyimpanan Kanopi:** Untuk setiap hari $t$:
   *   **Intersepsi ($I_t$, mm):** Air yang ditangkap oleh kapasitas kanopi kosong:
       $$I_t = \min(P_t, C_{\max} - S_{t-1})$$
       Di mana $P_t$ adalah curah hujan pada hari $t$, $S_{t-1}$ adalah penyimpanan yang ada, dan $C_{\max}$ adalah kapasitas kanopi maksimum ($LAI \times 0.2\text{ mm}$).
   *   **Evaporasi ($E_{\text{act}}$, mm):** Evaporasi air yang disimpan pada daun:
       $$E_{\text{act}} = \min(E_t, S_{t-1} + I_t)$$
   *   **Penyimpanan yang Diperbarui ($S_t$, mm):**
       $$S_t = S_{t-1} + I_t - E_{\text{act}}$$
       *(di mana $S_t \ge 0$)*
   *   **Total Intersepsi (L):** Dihitung sebagai $\sum E_{\text{act}} \times \text{Luas Tajuk} \times 1000$.

Secara default, mesin menjalankan neraca air harian ini menggunakan profil cuaca Asia Tenggara 365 hari. Untuk proyek tingkat lanjut, pengguna dapat mengunggah file data curah hujan per jam (yang diproses menggunakan ambang batas jeda kering 6 jam).

---

### 2.3 Penyerapan Polusi Udara

Deposisi kering polutan udara partikulat dan gas ($\text{PM}_{2.5}$, $\text{NO}_2$, $\text{O}_3$, $\text{SO}_2$) dimodelkan menggunakan **model deposisi kering resistance-in-series** (Baldocchi et al. 1987) untuk menghitung kecepatan deposisi harian ($V_d$, m/s):

$$V_d = \frac{1}{R_a + R_b + R_c}$$

Di mana:
*   **Hambatan Aerodinamis ($R_a$, s/m):** Diturunkan dari kecepatan angin $u$ (m/s) dan tinggi kanopi $h$ (m):
    $$R_a = \frac{\ln(10.0 + 20.0 / h)}{0.16 \cdot u}$$
*   **Hambatan Lapisan Batas Kuasi-Laminar ($R_b$, s/m):** Memodelkan lapisan batas daun:
    $$R_b = \frac{84.0}{\sqrt{u}}$$
*   **Hambatan Kanopi ($R_c$, s/m):**
    *   **Untuk PM2.5:** Memakai hambatan kanopi bawaan $R_c = 200.0\text{ s/m}$.
    *   **Untuk Gas:** Menggabungkan hambatan stomata ($R_s$), hambatan mesofil ($R_m = 10.0\text{ s/m}$), hambatan kutikula ($R_{\text{cut}} = 2000.0\text{ s/m}$), dan hambatan tanah ($R_g = 1000.0\text{ s/m}$) secara paralel:
        $$\frac{1}{R_c} = \frac{1}{R_s + R_m} + \frac{1}{R_{\text{cut}}} + \frac{1}{R_g}$$
        *Penutupan stomata* dimodelkan secara dinamis dengan menetapkan hambatan stomata siang hari $R_s = 100.0\text{ s/m}$ dan malam hari $R_s = 10000.0\text{ s/m}$ (mengurangi deposisi gas malam hari menjadi hampir nol). Kecepatan deposisi harian $V_d$ adalah rata-rata kecepatan siang dan malam hari.

Penyaringan polutan harian dihitung sebagai:
$$\text{Polutan Terfilter}_t = \text{Luas Daun} \times V_d \times \text{Konsentrasi} \times 86400$$

Di mana konsentrasi ambang batas dasar adalah $\text{PM}_{2.5} = 12.0\ \mu\text{g/m}^3$, $\text{NO}_2 = 40.0\ \mu\text{g/m}^3$, $\text{O}_3 = 100.0\ \mu\text{g/m}^3$, dan $\text{SO}_2 = 40.0\ \mu\text{g/m}^3$. Nilai ini diskalakan oleh `pollution_multiplier` dari profil tapak.

---

## 3. Integrasi Alur Kerja untuk Arsitek Lanskap & Surveyor

Treefolk Atlas menjembatani kesenjangan antara pengumpulan data lapangan, desain lanskap skematik, dan pelaporan dampak lingkungan.

```mermaid
flowchart TD
    subgraph Pengumpulan Data Lapangan & CAD
        A1[Surveyor: Inventarisasi Lapangan GPS/Total Station] -->|Ekspor GeoJSON/SHP/CSV| B1[Aset Pohon Terstandardisasi]
        A2[Arsitek Lanskap: Tata Letak Skematik] -->|Layer CAD Standar| B2[File Gambar CAD .DXF]
    end

    subgraph Parsing & Mesin Treefolk Atlas
        B1 --> C[Core Parser i-Tree SEA]
        B2 --> C
        C --> D{Pencarian Taksonomi Basis Data}
        D -->|1. Cocok Tepat| E[Basis Data Spesies]
        D -->|2. Fallback Genus| F[Rata-rata Berat Jenis & Pertumbuhan Genus]
        D -->|3. Fallback Keluarga/Famili| G[Default Pantropis]
    end

    subgraph Simulasi & Kotak Pasir (Sandbox) Skenario
        E & F & G --> H[Kalkulasi Inti Jasa Ekosistem]
        H --> I[Dashboard Interaktif & Sandbox Peta]
        I -->|Simulasi Penebangan/Penanaman 'What-If'| J[Ubah Spesies, Modifikasi Bentuk Tajuk, Override LAI]
    end

    subgraph Hasil Proyek & Pelaporan
        J --> K1[Laporan ESG & Sertifikat Imbal Jasa Karbon]
        J --> K2[Verifikasi Poin Green Mark / Greenship]
        J --> K3[Dokumen Kepatuhan AMDAL / UKL-UPL]
    end
    
    style B1 fill:#f9f,stroke:#333,stroke-width:2px
    style B2 fill:#bbf,stroke:#333,stroke-width:2px
    style I fill:#f96,stroke:#333,stroke-width:2px
    style K2 fill:#8f8,stroke:#333,stroke-width:2px
```

### 3.1 Untuk Surveyor (Audit Aset Kanopi yang Ada)
1.  **Pengumpulan Data Lapangan:** Surveyor merekam koordinat GPS, nama spesies (ilmiah atau lokal), DBH (cm), dan kondisi kesehatan pohon (Sangat Baik/Excellent hingga Mati/Dead).
2.  **Optimasi Tinggi-Diameter (H-D):** Dalam survei hutan kota tropis, mengukur tinggi setiap pohon secara manual membutuhkan waktu yang sangat lama dan sering terhalang oleh kanopi bertingkat yang rapat. Surveyor hanya perlu mengukur DBH. Mesin kalkulator akan secara otomatis menjalankan **model Weibull 3-parameter Feldpausch et al. (2012)** untuk memproyeksikan kurva tinggi asimtotik:
    $$H = a \times (1 - e^{-b \times D^c})$$
    *(menggunakan parameter regional Asia Tenggara: $a=57.122, b=0.0332, c=0.8468$ kecuali jika ada nilai spesifik spesies di basis data)*
3.  **Unggah Alur Kerja GIS:** Surveyor mengekspor hasil inventarisasi sebagai file GeoJSON atau Shapefile dan menjalankannya melalui CLI. Mesin secara otomatis mencocokkan berat jenis kayu taksonomi dan menghitung baseline jasa ekosistem saat ini.

### 3.2 Untuk Arsitek Lanskap (Desain Skematik & Perencanaan Usulan)
1.  **Standardisasi Layer CAD:** Arsitek menggambar rencana penanaman menggunakan konvensi layer standar di AutoCAD/Vectorworks:
    *   `L-PLNT-TREE-PROP` (Pohon baru yang diusulkan)
    *   `L-PLNT-TREE-EXST` (Pohon eksisting yang dipertahankan)
    *   `L-PLNT-TREE-RMVL` (Pohon eksisting yang akan ditebang/dibersihkan)
2.  **Parsing Langsung DXF:** Arsitek mengunggah file `.dxf` langsung ke platform. Aplikasi akan membaca posisi koordinat, menghitung jumlah simbol, memetakan atribut blok ke basis data spesies, dan mendeteksi kepadatan penanaman.
3.  **Perencanaan Skenario Interaktif (Sandbox):** Di area simulasi penanaman manual, desainer dapat:
    *   **Menguji Alternatif Spesies:** Mengganti pohon kayu keras lambat tumbuh seperti *Fagraea fragrans* (Tembusu, $\rho=0.82$, pertumbuhan $\Delta D=0.5\text{ cm/tahun}$) dengan pohon penangkap karbon cepat seperti *Samanea saman* (Trembesi, $\rho=0.45$, pertumbuhan $\Delta D=1.75\text{ cm/tahun}$) untuk mengoptimalkan target serapan karbon.
    *   **Simulasi Jarak Tanam Kanopi:** Menyesuaikan modifikator tajuk $k_{cw}$ (misalnya, memilih bentuk Kolumnar `0.08` untuk koridor sempit atau Melebar `0.28` untuk keteduhan maksimal) untuk mengevaluasi ruang ruang bebas tajuk dan menghindari tumpang tindih (crown overlapping).
    *   **Menilai Dampak Penebangan:** Melihat secara instan hilangnya kapasitas intersepsi air hujan dan penyaringan udara jika pohon dewasa pada layer `L-PLNT-TREE-RMVL` ditebang.

---

## 4. Akurasi Ilmiah, Batas Toleransi Kesalahan & Kalibrasi

Untuk menjamin data kelas rekayasa (engineering-grade), platform ini menggunakan regresi kehutanan tropis yang telah ditinjau sejawat (peer-reviewed), bukan padanan wilayah beriklim sedang.

| Komponen Kalkulasi | Model Ilmiah Acuan | Batas Kesalahan Terdekat (Error Margin) | Faktor Kalibrasi & Batasan |
| :--- | :--- | :--- | :--- |
| **Biomassa Dikotil (AGB)** | Regresi Pantropis Chave et al. (2014) | $\pm 5\% - 10\%$ (Tingkat Tegakan)<br>$\pm 10\% - 15\%$ (Individu Pohon) | Secara langsung memasukkan berat jenis kayu ($\rho$) dan tinggi pohon. Menyesuaikan bentuk tumbuh perkotaan menggunakan faktor penyesuaian dinamis berbasis CLE: $f_{\text{urban}} = 0.8 + 0.04 \times (5 - CLE)$. |
| **Biomassa Palem (AGB)** | Rumus Silinder Frangi & Lugo (1985) | $\pm 10\% - 15\%$ | Menggunakan rumus volume silinder khusus ($0.07854 \times \rho \times D^2 \times H$). Menghilangkan kesalahan estimasi berlebih sebesar $200\% - 300\%$ dari rumus dikotil. |
| **Intersepsi Air Hujan (Stormwater)** | Evaporasi Kanopi Basah Harian Penman-Monteith | $\pm 10\% - 15\%$ | Digerakkan oleh suhu harian, kecepatan angin, kelembaban relatif, dan curah hujan harian. Melacak kejenuhan kanopi dan limpasan air secara dinamis. |
| **Penyerapan Polusi Udara** | Model Hambatan Deposisi Kering Baldocchi | $\pm 15\% - 20\%$ | Menghitung kecepatan deposisi kering harian ($V_d = 1 / [R_a + R_b + R_c]$). Memodelkan penutupan stomata secara dinamis (malam hari $R_s \to 10000$ s/m). |
| **Prakiraan Pertumbuhan** | Model Pertumbuhan Sigmoidal Chapman-Richards | $\pm 5\%$ | Menggantikan pertambahan linier dengan kurva pertumbuhan sigmoidal asimtotik: $\Delta D = k \cdot DBH \cdot ((DBH_{\max}/DBH)^{1/3} - 1)$. |

---

## 5. Perbandingan Fitur: i-Tree Eco vs. Treefolk Atlas (i-Tree SEA)

| Parameter Evaluasi | i-Tree Eco v6 Standar USDA | Treefolk Atlas (i-Tree SEA) | Dampak & Rationale Lokal |
| :--- | :--- | :--- | :--- |
| **Baseline Iklim** | Wilayah Beriklim Sedang / Utara (AS/Eropa) | Dataran Rendah Tropis Asia Tenggara (Zona Af/Am) | Menghilangkan batas pertumbuhan berbasis suhu dingin dan pembekuan (frost) yang tidak relevan di daerah tropis. |
| **Prakiraan Pertumbuhan** | Tabel pertumbuhan US Forest Service | Kurva Sigmoidal Chapman-Richards | Menghindari biomassa tak terbatas pada pohon dewasa; memodelkan batas asimtotik spesifik spesies ($DBH_{\max}$). |
| **Pemodelan Palem (Monokotil)** | Persamaan alometrik dikotil standar (menyebabkan overestimate parah) | Model khusus Volume Batang Silindris | Mengukur biomassa palem secara akurat; krusial untuk proyek tropis di mana palem mendominasi 20%–40% area lanskap. |
| **Pemetaan Berat Jenis Kayu** | Penyesuaian rasio berat jenis post-hoc | Pemasukan langsung nilai $\rho$ ke rumus biomassa | Menjamin akurasi taksonomi dengan menggunakan nilai berat jenis kayu dasar dari basis data lokal secara langsung. |
| **Input Tinggi Pohon** | Wajib diukur di lapangan | Proyeksi H-D Weibull (Feldpausch 2012) | Mempercepat survei lapangan; tinggi pohon diproyeksikan secara otomatis jika data lapangan tidak tersedia. |
| **Integrasi Desain CAD/GIS** | Tidak didukung langsung | Mendukung parsing DXF asli dan georeferensi Shapefile | Terhubung langsung dengan format kerja utama para profesional lanskap dan surveyor (AutoCAD, QGIS, ArcGIS). |
| **Metode Stormwater** | Neraca air per jam | Neraca air kanopi basah harian (Penman) | Memungkinkan pelacakan intersepsi musiman yang sangat akurat tanpa memerlukan data stasiun cuaca lengkap. |
| **Metode Polusi** | Model deposisi per jam | Deposisi kering harian resistance-in-series (Baldocchi) | Mempertimbangkan hambatan lapisan batas dan penutupan stomata diurnal (penutupan malam hari) untuk akurasi tinggi. |
| **Tahapan Evaluasi** | Inventarisasi & pengelolaan pasca-penanaman | Perencanaan konsep, desain skematik, dan pemodelan dampak | Memungkinkan arsitek mengoptimalkan desain ekologis *sebelum* pembangunan fisik dimulai. |

---

## 6. Kasus Penggunaan Utama & Area Penerapan

### 6.1 Sertifikasi Bangunan Hijau (BCA Green Mark, Greenship)
Di bawah sistem pemeringkatan bangunan hijau (seperti **BCA Green Mark 2021** di Singapura pada kategori *Health and Well-being (Hw)*, atau **GBCI Greenship** di Indonesia pada kategori *Appropriate Site Development (ASD)*), proyek mendapatkan poin tambahan jika berhasil melestarikan pohon dewasa yang ada dan memperluas area kanopi hijau.
*   **Penerapan:** Desainer dapat menghasilkan laporan total penyimpanan karbon dan volume air hujan tahunan yang berhasil ditahan di lokasi. Output dari alat ini berfungsi sebagai dokumen kepatuhan (compliance) resmi yang diaudit untuk mengamankan kredit biophilic design dan urban greenery.

### 6.2 Pelaporan ESG Korporat & Offsetting Karbon
Perusahaan saat ini dituntut untuk menunjukkan strategi pengurangan emisi karbon yang nyata demi memenuhi kriteria Lingkungan, Sosial, dan Tata Kelola (ESG).
*   **Penerapan:** Pengembang properti memodelkan potensi penyerapan karbon jangka panjang (misalnya 30 tahun) dari kawasan yang mereka bangun. Hasil ekspor PDF dari Treefolk Atlas memberikan data kuantitatif yang valid untuk klaim net-zero korporat, yang dikonversi ke setara lingkungan seperti penghematan bensin atau jarak mengemudi mobil yang dihindari.

### 6.3 Analisis Mengenai Dampak Lingkungan (AMDAL / UKL-UPL) & Izin Penebangan Pohon
Pemerintah daerah semakin memperketat regulasi penebangan pohon di area perkotaan. Pengembang harus memberikan ganti rugi ekologis jika menebang pohon dewasa.
*   **Penerapan:** Surveyor memetakan pohon eksisting yang akan ditebang pada layer `L-PLNT-TREE-RMVL`. Sistem akan menghitung kerugian jasa ekologis yang hilang. Arsitek lanskap kemudian merancang rencana penanaman pohon pengganti pada layer `L-PLNT-TREE-PROP` untuk membuktikan kepada dinas terkait bahwa dalam waktu sekian tahun, area tersebut akan mencapai kesetaraan ekologis kembali.

### 6.4 Hidrologi Perkotaan & Sistem Drainase Berkelanjutan (SuDS)
Urbanisasi yang cepat di Asia Tenggara meningkatkan risiko banjir limpasan akibat berkurangnya area resapan.
*   **Penerapan:** Insinyur sipil dan arsitek lanskap menggunakan simulasi penahanan air hujan di area sandbox untuk membandingkan efektivitas jenis tajuk. Mereka dapat memilih tata letak pohon dengan tajuk melebar (*Samanea saman*, $k_{cw}=0.28$) daripada pohon pilar (*Polyalthia longifolia*, $k_{cw}=0.08$) untuk mengoptimalkan penyerapan limpasan air hujan di kawasan padat yang rawan genangan.
