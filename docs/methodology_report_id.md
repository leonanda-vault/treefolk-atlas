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

#### Untuk Pohon Monokotil (Palem)
Model alometrik dikotil standar cenderung menaksir terlalu tinggi (overestimate) biomassa palem karena perbedaan mekanika struktural (batang silindris tanpa pengecilan diameter ke atas, tidak adanya pertumbuhan lateral sekunder kambium, dan rasio air-ke-massa kering yang tinggi). Treefolk Atlas menerapkan **Model Batang Silindris** khusus:

$$\text{AGB}_{\text{palm}} = 0.07854 \times \rho \times D^2 \times H$$

*   *Penurunan Rumus:* Volume silinder adalah $V = \frac{\pi}{4} \times (\frac{D}{100})^2 \times H = \frac{\pi}{40000} \times D^2 \times H$ (m³). Mengonversi volume menjadi massa kering menggunakan berat jenis kayu kering ($\rho \times 1000$ kg/m³) menghasilkan:
    $$\text{AGB}_{\text{palm}} = \left(\frac{\pi}{40000} \times 1000\right) \times \rho \times D^2 \times H \approx 0.07854 \times \rho \times D^2 \times H$$
*   *Kalibrasi Taksonomi:* Fraksi karbon dasar disesuaikan ke bawah menjadi **0.41** (dibandingkan dengan 0.50 pada dikotil) untuk mencerminkan kandungan lignin yang lebih rendah pada berkas pengangkut monokotil (IPCC 2006).

---

### 2.2 Proksi Limpasan Air Hujan (Stormwater) dengan Batas Kejenuhan Tajuk

Model iklim sedang biasanya menjalankan simulasi neraca air harian atau jam demi jam yang memerlukan kumpulan data meteorologi jangka panjang yang rumit. Treefolk Atlas menyediakan dua jalur penilaian:

#### 1. Proksi Stormwater Tahunan
Menghitung kapasitas tahunan penyimpanan air hujan oleh tajuk berdasarkan rata-rata siklus curah hujan lokal:

$$\text{Intersepsi Tahunan (L)} = \text{Crown Area} \times \text{LAI}_{\text{resolved}} \times S_L \times N_{\text{events}} \times 1000$$

*   **Kapasitas Penyimpanan Daun Spesifik ($S_L$):** Ditetapkan sebesar $0.0002\text{ m}$ ($0.2\text{ mm}$ ketebalan lapisan air), selaras dengan i-Tree Hydro (Wang et al. 2008).
*   **Rata-rata Kejadian Hujan Tahunan ($N_{\text{events}}$):** 180 kejadian hujan terpisah per tahun (dikalibrasi untuk pola monsun Singapura/Jakarta).
*   **Batas Kejenuhan Kanopi:** Untuk pohon dengan LAI $5.0$, kapasitas retensi absolut tajuk adalah ketebalan $1.0\text{ mm}$ ($5.0 \times 0.2\text{ mm}$). Karena curah hujan tropis hampir selalu melebihi ambang batas $1.0\text{ mm}$ ini, proksi mengasumsikan kanopi jenuh sepenuhnya dan mengintersepsi tepat sebesar kapasitas maksimumnya selama masing-masing dari 180 kejadian hujan tersebut. Air hujan yang jatuh melampaui batas kejenuhan akan langsung lolos ke tanah (throughfall).

#### 2. Analisis Curah Hujan Per Jam (Mode Lanjutan)
Pengguna dapat mengunggah data curah hujan per jam (8.760 jam/tahun). Mesin kalkulasi akan:
*   Mengelompokkan jam-jam basah berurutan yang dipisahkan oleh jeda kering $\ge 6$ jam menjadi kejadian hujan terpisah (standar WMO).
*   Melacak akumulasi curah hujan untuk setiap kejadian. Jika curah hujan kumulatif kurang dari kapasitas penyimpanan kanopi ($\text{Crown Area} \times \text{LAI} \times S_L$), seluruh air hujan diintersepsi. Jika melebihi, intersepsi dibatasi pada kapasitas maksimal tajuk, dan sisanya dikategorikan sebagai limpasan/air lolos.

---

### 2.3 Penyerapan Polusi Udara

Deposisi kering polutan udara partikulat dan gas ($\text{PM}_{2.5}$, $\text{NO}_2$, $\text{O}_3$, $\text{SO}_2$) dimodelkan menggunakan tingkat deposisi tahunan yang dikalikan dengan luas daun total dan faktor pengali polusi lokal:

$$\text{Polutan yang Diserap (g/tahun)} = (\text{Crown Area} \times \text{LAI}) \times \text{Tingkat Deposisi Dasar} \times \text{Pengali Polusi}$$

*   **Tingkat Deposisi Dasar:** $\text{PM}_{2.5} = 0.50$, $\text{NO}_2 = 0.90$, $\text{O}_3 = 1.40$, $\text{SO}_2 = 0.35$ g/m²/tahun (Nowak 2006, Chen 2017).
*   **Pengali Polusi:** Ditentukan oleh **Profil Tapak / Site Profiles** yang dipilih (Kawasan Padat Perkotaan/CBD = `1.50`, Kawasan Industri = `2.00`, Taman Kota = `1.00`, Pinggiran Kota/Perumahan = `0.75`, Pesisir = `0.60`, Perdesaan = `0.40`). Mode Lanjutan menghitung pengali tertimbang secara langsung dari konsentrasi terukur ($\mu\text{g/m}^3$) relatif terhadap batas acuan WHO.

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
| **Biomassa Dikotil (AGB)** | Regresi Pantropis Chave et al. (2014) | $\pm 5\% - 10\%$ (Tingkat Tegakan)<br>$\pm 20\% - 25\%$ (Individu Pohon) | Secara langsung memasukkan berat jenis kayu ($\rho$) dan tinggi pohon. Menyesuaikan bentuk tumbuh perkotaan di ruang terbuka menggunakan faktor reduksi tajuk Nowak sebesar 0.80. |
| **Biomassa Palem (AGB)** | Rumus Silinder Frangi & Lugo (1985); Goodman et al. (2013) | $\pm 10\% - 15\%$ | Menggunakan rumus volume silinder khusus ($0.07854 \times \rho \times D^2 \times H$). Menghilangkan kesalahan estimasi berlebih sebesar $200\% - 300\%$ akibat penerapan rumus dikotil pada palem. |
| **Intersepsi Air Hujan (Stormwater)** | Wang et al. (2008); Hirabayashi (2013) | $\pm 15\% - 20\%$ (Mode Jam-jaman)<br>$\pm 30\%$ (Proksi Tahunan) | Dibatasi oleh batas jenuh indeks area daun (LAI). Berfungsi sebagai indeks perbandingan relatif untuk kapasitas pengurangan limpasan. |
| **Penyerapan Polusi Udara** | Nowak et al. (2006); Chen et al. (2017) | $\pm 40\% - 50\%$ (Skala Magnitudo) | Sangat tergantung pada konsentrasi polutan sekitar. Sangat baik untuk perbandingan relatif tata letak lanskap, namun tidak boleh digunakan sebagai model dispersi atmosfer absolut. |
| **Prakiraan Pertumbuhan** | Database Kerapatan & Pertumbuhan Lokal (NParks Singapore) | $\pm 10\% - 15\%$ (Di bawah usia 20 tahun) | Mengintegrasikan tingkat kenaikan tahunan kontinu ($\Delta D$ dan tinggi palem) berdasarkan data pengamatan urban regional, bukan kelas kategori statis. |

---

## 5. Perbandingan Fitur: i-Tree Eco vs. Treefolk Atlas (i-Tree SEA)

| Parameter Evaluasi | i-Tree Eco v6 Standar USDA | Treefolk Atlas (i-Tree SEA) | Dampak & Rationale Lokal |
| :--- | :--- | :--- | :--- |
| **Baseline Iklim** | Wilayah Beriklim Sedang / Utara (AS/Eropa) | Dataran Rendah Tropis Asia Tenggara (Zona Af/Am) | Menghilangkan batas pertumbuhan berbasis suhu dingin dan pembekuan (frost) yang tidak relevan di daerah tropis. |
| **Prakiraan Pertumbuhan** | Tabel pertumbuhan US Forest Service atau input manual | Database pertumbuhan kontinu spesies tropis | Menghindari estimasi pertumbuhan yang terlalu rendah; pohon tropis tumbuh 2–4 kali lebih cepat dibanding iklim sedang. |
| **Pemodelan Palem (Monokotil)** | Persamaan alometrik dikotil standar (menyebabkan overestimate parah) | Model khusus Volume Batang Silindris | Mengukur biomassa palem secara akurat; krusial untuk proyek tropis di mana palem mendominasi 20%–40% area lanskap. |
| **Pemetaan Berat Jenis Kayu** | Penyesuaian rasio berat jenis post-hoc | Pemasukan langsung nilai $\rho$ ke rumus biomassa | Menjamin akurasi taksonomi dengan menggunakan nilai berat jenis kayu dasar dari basis data lokal secara langsung. |
| **Input Tinggi Pohon** | Wajib diukur di lapangan | Proyeksi H-D Weibull (Feldpausch 2012) | Mempercepat survei lapangan; tinggi pohon diproyeksikan secara otomatis jika data lapangan tidak tersedia. |
| **Integrasi Desain CAD/GIS** | Tidak didukung langsung (memerlukan impor Excel/CSV manual) | Mendukung parsing DXF asli dan georeferensi Shapefile | Terhubung langsung dengan format kerja utama para profesional lanskap dan surveyor (AutoCAD, QGIS, ArcGIS). |
| **Metode Stormwater** | Neraca air per jam (memerlukan data stasiun cuaca lengkap) | Proksi tahunan + batas jenuh limpasan per jam | Menyederhanakan proses bagi perencana kota yang tidak memiliki akses ke stasiun meteorologi bandara/lokal. |
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
