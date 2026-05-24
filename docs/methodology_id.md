# i-Tree SEA — Dokumentasi Metodologi

> **Versi:** 0.3.0-alpha · **Pembaruan terakhir:** Mei 2026
> **Referensi Mesin:** Metode i-Tree Eco v6.0.22+, diadaptasi untuk kehutanan perkotaan tropis Asia Tenggara

---

## 1. Ringkasan Umum

i-Tree SEA adalah adaptasi sumber terbuka dari metodologi [USDA Forest Service i-Tree](https://www.itreetools.org) yang dikalibrasi khusus untuk kehutanan perkotaan tropis di Asia Tenggara. Aplikasi ini memperkirakan jasa ekosistem yang disediakan oleh pohon individu menggunakan persamaan alometrik, model pertumbuhan, dan perhitungan proksi lingkungan.

### Jasa Ekosistem yang Dihitung

| Layanan | Satuan | Metode |
| :--- | :--- | :--- |
| Penyimpanan Karbon | kg C | Biomassa alometrik → konversi karbon |
| Penyerapan Karbon | kg C/tahun | Selisih penyimpanan tahunan (delta-storage) |
| Ekuivalen CO₂ | kg CO₂ | Rasio stoikiometri IPCC (3.6663) |
| Produksi Oksigen | kg O₂/tahun | Stoikiometri fotosintesis (2.6667) |
| Ekuivalensi EPA | galon/mil | Kalkulator Ekuivalensi GRK US EPA |
| Intersepsi Air Hujan | L/tahun | Proksi kapasitas penyimpanan kanopi |
| Penyaringan Polusi Udara (PM2.5, NO₂, O₃, SO₂) | g/tahun | Proksi deposisi permukaan daun |

### Batasan Ruang Lingkup

- **Alat Fase Desain:** Ditujukan bagi arsitek lanskap untuk mengevaluasi rencana penanaman, bukan untuk inventarisasi hutan pasca-konstruksi.
- **Resolusi Pohon Individu:** Tidak memodelkan persaingan antar pohon atau tingkat kematian di tingkat tegakan.
- **Fokus Tropis:** Parameter dikalibrasi untuk wilayah dataran rendah tropis basah Asia Tenggara (Köppen Af/Am).

---

## 2. Penyimpanan Karbon

### 2.1 Biomassa Di Atas Tanah (AGB)

Kami menerapkan dua bentuk persamaan dari metodologi i-Tree Eco:

#### Utama: Model Pantropis Chave et al. (2014)

Ketika tinggi pohon tersedia:

$$\text{AGB} = 0.0673 \times (\rho \times D^2 \times H)^{0.976}$$

| Simbol | Arti | Satuan |
| :--- | :--- | :--- |
| AGB | Biomassa kering di atas tanah | kg |
| $\rho$ | Berat jenis kayu (wood density) | g/cm³ |
| D | Diameter setinggi dada (DBH) | cm |
| H | Tinggi total pohon | m |

> **Sumber:** Chave, J., et al. (2014). "Improved allometric models to estimate the aboveground biomass of tropical trees." *Global Change Biology*, 20(10), 3177–3190.

#### Alternatif: Persamaan Tanpa Tinggi Pohon

Ketika tinggi pohon tidak diukur (umum pada rencana penanaman fase desain):

$$\ln(\text{AGB}) = -1.803 + (-0.976) \cdot E + 0.976 \cdot \ln(\rho) + 2.673 \cdot \ln(D) + (-0.0299) \cdot [\ln(D)]^2$$

| Simbol | Nilai | Sumber |
| :--- | :--- | :--- |
| E | -0.070 | Stres bioklimatik untuk Asia Tenggara ekuator (Chave 2014, Tabel S3) |

#### Sekunder: Model Hutan Sekunder Ketterings et al. (2001)

Untuk spesies tertentu yang beradaptasi di hutan sekunder Indonesia (misalnya, *Trema orientalis*, *Macaranga* spp.):

$$\text{AGB} = a \times \rho \times D^b$$

| Simbol | Nilai Default | Sumber |
| :--- | :--- | :--- |
| a | 0.11 | Ketterings et al. (2001) |
| b | 2.62 | Ketterings et al. (2001) |

---

## 3. Penyerapan Karbon

### 3.1 Metode Delta-Storage

Penyerapan kotor tahunan dihitung berdasarkan perubahan penyimpanan karbon selama satu tahun pertumbuhan:

$$\text{Penyerapan} = \text{C\_storage}(D + \Delta D) - \text{C\_storage}(D)$$

Dimana $\Delta D$ adalah pertumbuhan DBH tahunan berdasarkan kelas pertumbuhan spesies:

| Kecepatan Tumbuh | $\Delta D$ (cm/tahun) | Keterangan |
| :--- | :--- | :--- |
| Lambat | 0.50 | Diadaptasi dari i-Tree Eco & data pertumbuhan NParks |
| Sedang | 1.00 | Standar default i-Tree Eco |
| Cepat | 1.75 | Diadaptasi untuk spesies tropis tumbuh cepat |

### 3.2 Batas Maksimum Pohon Besar

Ketika penyimpanan karbon melebihi **7.500 kg**, laju penyerapan dibatasi maksimal **40 kg per cm pertumbuhan DBH** untuk mencegah estimasi yang tidak realistis pada pohon yang sangat besar.

---

## 4. Karbon Dioksida (CO₂) dan Oksigen (O₂)

### 4.1 Ekuivalen CO₂

Karbon elemental dikonversi menjadi ekuivalen karbon dioksida ($\text{CO}_2\text{e}$) menggunakan rasio stoikiometri IPCC (44/12 ≈ 3.6663):

$$\text{Ekuivalen } \text{CO}_2 \text{ (kg)} = \text{Karbon (kg)} \times 3.6663$$

### 4.2 Produksi Oksigen

Diestimasi secara stoikiometri dari penyerapan karbon bersih berdasarkan fotosintesis (rasio 32/12 ≈ 2.6667):

$$\text{Produksi Oksigen Tahunan (kg/tahun)} = \text{Penyerapan Karbon Bersih (kg/tahun)} \times 2.6667$$

---

## 5. Kesetaraan Lingkungan (Konversi Metrik)

Untuk membuat metrik penyerapan karbon lebih mudah dipahami oleh pemangku kepentingan non-teknis, alat ini mengonversi penyerapan CO₂ tahunan menjadi bentuk kesetaraan nyata menggunakan Kalkulator Ekuivalensi Gas Rumah Kaca US EPA, yang dikonversi ke dalam satuan metrik serta faktor lokal tambahan.

```
Bensin yang Dihemat (Liter) = (Penyerapan CO₂ Tahunan dalam Ton Metrik) × 112.18 × 3.78541 ≈ (Penyerapan CO₂ Tahunan dalam Ton Metrik) × 424.65
Jarak Mengemudi Mobil yang Dihindari (km) = (Penyerapan CO₂ Tahunan dalam Ton Metrik) × 2564.0 × 1.60934 ≈ (Penyerapan CO₂ Tahunan dalam Ton Metrik) × 4126.36
Jarak Mengemudi Motor yang Dihindari (km) = (Penyerapan CO₂ Tahunan dalam kg) × 20.0
Pengisian Daya Ponsel (Kali) = (Penyerapan CO₂ Tahunan dalam kg) × 80.645
```

- **Faktor sepeda motor (20.0 km/kg CO₂)** didasarkan pada emisi rata-rata sebesar 0.05 kg CO₂/km untuk sepeda motor berkapasitas mesin kecil yang umum digunakan di Asia Tenggara.
- **Faktor Pengisian Daya Ponsel (80.645 kali/kg CO₂)** sesuai dengan faktor US EPA sebesar 80.645 pengisian daya per ton metrik CO₂ (sekitar 0.0124 kg CO₂ per sekali pengisian daya).

> **Sumber:** Kalkulator Ekuivalensi GRK US EPA dan basis data emisi transportasi regional.
> **Status:** ✅ Diimplementasikan (dikonversi ke metrik: 1 galon ≈ 3.78541 L; 1 mil ≈ 1.60934 km; ditambah proksi spesifik regional).

---

## 6. Estimasi Tinggi Pohon

Ketika tinggi pohon tidak diukur (umum pada rencana penanaman), kami mengestimasi tinggi dari DBH menggunakan model hukum pangkat (power-law):

$$\text{H} = a \times D^b$$

| Parameter | Nilai Default | Sumber |
|:---|:---|:---|
| a | 0.893 | Feldpausch et al. (2012) — Tropis basah Asia Tenggara |
| b | 0.760 | Feldpausch et al. (2012) |

Parameter tinggi spesifik-spesies disimpan di database dan mengesampingkan nilai default ini jika tersedia.

> **Status:** ✅ Sesuai untuk fase desain. i-Tree Eco mengukur tinggi secara langsung; kami mengestimasinya.

---

## 7. Intersepsi Air Hujan

### 7.1 Pendekatan Model

i-Tree Eco menggunakan model keseimbangan air hidrologis penuh (Wang et al. 2008, Hirabayashi 2013) yang memerlukan data curah hujan per jam dan membandingkan skenario limpasan dengan pohon vs tanpa pohon.

i-Tree SEA menggunakan **proksi yang disederhanakan** untuk memperkirakan volume intersepsi kanopi tahunan:

$$\text{Intersepsi Tahunan (L)} = \text{Luas Tajuk} \times \text{LAI} \times S_L \times N_{\text{events}} \times 1000$$

| Parameter | Nilai / Rumus | Sumber / Keterangan |
|:---|:---|:---|
| Luas Tajuk | $\pi \times (\text{CW}/2)^2$ di mana $\text{CW} = 0.6 + 0.15 \times \text{DBH}$ (maks 20m) | Peper et al. (2001), diadaptasi |
| LAI | 5.0 | Asner et al. (2003), daun lebar tropis |
| $S_L$ (penyimpanan daun spesifik) | 0.0002 m (0.2 mm) | i-Tree Hydro (Wang et al. 2008) |
| $N_{\text{events}}$ | 180 kejadian hujan/tahun | Badan Meteorologi regional (e.g. Singapura/BMKG) |

### 7.2 Perbandingan dengan i-Tree Eco

| Aspek | i-Tree Eco | i-Tree SEA |
|:---|:---|:---|
| Resolusi temporal | Per jam | Proksi tahunan |
| Data curah hujan | Data pencatat curah hujan per jam | Jumlah kejadian rata-rata |
| Permukaan tanah | Pemisahan kedap/lulus air | Tidak dimodelkan |
| Melalui tajuk (Throughfall) | Dimodelkan | Tidak dimodelkan |
| Penyimpanan cekungan | Dimodelkan | Tidak dimodelkan |

> **Status:** ⚠️ Proksi yang disederhanakan. Cocok untuk peringkat perbandingan antara opsi penanaman, bukan untuk pemodelan hidrologi mutlak. Untuk analisis limpasan air hujan yang mendalam, gunakan i-Tree Hydro+ atau model khusus.

### 7.3 Profil Lokasi (Site Profiles)

Alih-alih memaparkan parameter lingkungan mentah kepada pengguna, i-Tree SEA membundel curah hujan, konsentrasi polusi, dan LAI ke dalam **Profil Lokasi** — konteks lingkungan yang telah dikonfigurasi sebelumnya berdasarkan jenis penggunaan lahan. Hal ini membuat aplikasi dapat diakses oleh arsitek lanskap yang mungkin tidak memiliki data meteorologi.

| Profil | Kejadian Hujan/tahun | Pengali Polusi | LAI | Rasional |
|:---|:---|:---|:---|:---|
| **Urban Dense (CBD / Roadside)** | 180 | 1.50× | 4.0 | Polusi sekitar yang tinggi dekat lalu lintas; kepadatan kanopi berkurang |
| **Urban Park / Campus** | 180 | 1.00× (baseline) | 5.0 | Default standar literatur untuk daun lebar tropis |
| **Suburban / Residential** | 180 | 0.75× | 5.0 | Polusi sekitar lebih rendah di area perumahan |
| **Industrial / Port Area** | 170 | 2.00× | 3.5 | Polusi sangat tinggi; kanopi jarang; kejadian hujan lebih sedikit |
| **Coastal / Waterfront** | 170 | 0.60× | 4.5 | Udara laut bersih; kanopi terpangkas angin |
| **Peri-Urban / Rural Edge** | 190 | 0.40× | 6.0 | Polusi rendah; potensi kanopi lebat; lebih banyak hujan |

**Pengali polusi** menyelaraskan tingkat penyaringan dasar (Nowak et al. 2006) untuk mencerminkan konsentrasi polutan aktual sekitar. Konsentrasi yang lebih tinggi berarti lebih banyak polutan yang tersedia untuk deposisi kering, hingga batas kecepatan deposisi. Nilai dikalibrasi terhadap data kualitas udara kota WHO dan IQAir untuk area perkotaan di Asia Tenggara.

> **Catatan:** Pengguna memilih satu profil lokasi di bilah samping dasbor sebelum menjalankan perhitungan. Profil yang dipilih berlaku seragam untuk semua pohon dalam analisis.

### 7.4 Mode Kustom / Lanjutan

Untuk proyek dengan data lingkungan spesifik-lokasi, i-Tree SEA menawarkan profil **Kustom / Lanjutan** yang menggantikan nilai prasetel dengan pengukuran yang disediakan pengguna:

#### Unggah Curah Hujan Per Jam
Pengguna dapat mengunggah CSV data curah hujan per jam (mm). Mesin:
1. Mengidentifikasi kejadian hujan diskrit (jam basah berturut-turut yang dipisahkan oleh $\ge 6$ jam kering, mengikuti konvensi WMO).
2. Untuk setiap kejadian, membatasi intersepsi kanopi pada kapasitas penyimpanan maksimum pohon (`Luas Tajuk × LAI × S_L`).
3. Kejadian ringan diintersepsi sepenuhnya; kejadian lebat meluap — ini lebih akurat daripada proksi sederhana.

**Format CSV:** Kolom tunggal, satu nilai per baris, header opsional (atau header `rain_mm`). 8.760 baris = 1 tahun data per jam. Sumber data mencakup layanan meteorologi nasional (BMKG untuk Indonesia, MSS untuk Singapura) atau analisis ulang ECMWF ERA5.

#### Konsentrasi Polusi Sekitar
Pengguna memasukkan rata-rata konsentrasi tahunan terukur untuk PM2.5, NO₂, O₃, dan SO₂ dalam µg/m³. Mesin menghitung pengali polusi tertimbang:

$$\text{multiplier} = \sum(\text{measured}_i / \text{baseline}_i \times \text{weight}_i) / \sum(\text{weight}_i)$$

Di mana baseline adalah konsentrasi yang diasumsikan oleh Nowak et al. (2006), dan bobot adalah tingkat penyaringan dasar. Ini memastikan polutan dengan potensi penyaringan lebih tinggi berkontribusi secara proporsional lebih besar terhadap pengali agregat.

| Polutan | Baseline (µg/m³) | Sumber |
|:---|:---|:---|
| PM2.5 | 12.0 | Standar tahunan US EPA NAAQS |
| NO₂ | 40.0 | Rata-rata tahunan pedoman WHO |
| O₃ | 100.0 | Rata-rata 8 jam pedoman WHO |
| SO₂ | 40.0 | Batas 24 jam pedoman WHO |

#### LAI Kustom
Pengguna dapat menyesuaikan Indeks Area Daun untuk mencocokkan kondisi kanopi spesifik lokasi (misalnya, 3.0–4.0 untuk pohon tepi pantai yang terpangkas angin, 6.0–8.0 untuk hutan sekunder lebat).

---

## 8. Penyaringan Polusi Udara

### 8.1 Pendekatan Model

i-Tree Eco menggunakan model deposisi kering per jam yang menggabungkan:
- Data konsentrasi polusi udara lokal
- Kecepatan deposisi (tergantung spesies)
- Luas area daun
- Kondisi meteorologi (angin, tinggi lapisan batas)

i-Tree SEA menggunakan **laju proksi tahunan** (g/m² luas daun/tahun):

| Polutan | Laju (g/m²/tahun) | Sumber |
|:---|:---|:---|
| PM2.5 | 0.50 | Chen et al. (2017), analog tropis |
| NO₂ | 0.90 | Nowak et al. (2006), default i-Tree Eco |
| O₃ | 1.40 | Nowak et al. (2006), default i-Tree Eco |
| SO₂ | 0.35 | Nowak et al. (2006), default i-Tree Eco |

$$\text{Polutan Terfilter (g/tahun)} = \text{Luas Daun (m}^2\text{)} \times \text{Laju (g/m}^2\text{/tahun)}$$

> **Status:** ⚠️ Proksi yang disederhanakan. Menggunakan nilai median penyaringan dari literatur alih-alih pemodelan deposisi per jam. Memberikan estimasi tingkat magnitudo untuk perbandingan desain.

---

## 9. Database Spesies

### 9.1 Sumber Data

| Sumber | Data yang Digunakan | Jumlah |
|:---|:---|:---|
| Global Wood Density Database (Chave 2009, Zanne 2009) | Berat jenis kayu ($\rho$) | Semua spesies |
| Berat jenis kayu ICRAF World Agroforestry | $\rho$ spesies tropis | Tambahan |
| Database pohon NParks Singapura | Daftar spesies, laju tumbuh | 15 spesies |
| Database Pohon Perkotaan McPherson et al. (2016) | Validasi alometrik | Referensi |
| GlobAllomeTree (2017) | Formulir persamaan tambahan | Referensi |

### 9.2 Skema Fallback Resolusi Spesies

Ketika mencari koefisien alometrik, mesin mengikuti fallback 3 tingkat:

```
1. Kesesuaian tingkat spesies → nama ilmiah persis
2. Kesesuaian tingkat genus   → genus sama, koefisien dirata-rata
3. Default pantropis          → Chave 2014 dengan default ρ = 0.58 g/cm³
```

> **Status:** ✅ Sesuai dengan strategi resolusi i-Tree Eco (spesies → genus → famili → default kayu keras/konifer).

### 9.3 Jumlah Spesies Saat Ini

**85 spesies** di dalam database, mencakup:
- Pohon perkotaan umum di NParks Singapura
- Spesies lanskap Indonesia (Dinas Pertamanan)
- Pohon buah Asia Tenggara, palem, dan spesies asli
- Tanaman hias pantropis yang umum

---

## 10. Prakiraan Pertumbuhan Multi-Tahun

### 10.1 Metode

Pengguna dapat menyesuaikan jangka waktu prakiraan dari **1 hingga 100 tahun**, memungkinkan pemantauan jangka pendek maupun pemodelan jangka panjang. Mesin melacak pertumbuhan absolut ($\Delta\text{DBH}$ dan $\Delta\text{Tinggi}$) bersama dengan manfaat yang diperoleh.

Mulai dari DBH awal (default 5 cm untuk pohon baru, diukur untuk pohon eksisting):

```
Untuk setiap tahun 0..N:
    DBH(t) = DBH(0) + ΔD × t
    Tinggi(t) = H(0) × [DBH(t) / DBH(0)]^0.5
    Biomass(t) = hitung_biomassa(DBH(t), H(t))
    Penyerapan(t) = Karbon(t) - Karbon(t-1)
    Air Hujan(t) = proksi_intersepsi(DBH(t))
    Polusi(t) = proksi_penyaringan(DBH(t))
```

### 10.2 Estimasi Tinggi dan Model Pertumbuhan

Jika tinggi pohon tidak disediakan dalam CAD atau data lapangan, i-Tree SEA mengestimasinya dari DBH menggunakan model pantropis **Feldpausch et al. (2012)**. Mesin mendukung dua bentuk persamaan:

1. **Hukum Pangkat / Power-law (fallback):** $H = a \times D^b$
2. **Weibull (pilihan utama):** $H = a \times (1 - e^{-b \times D^c})$

Model Weibull lebih akurat untuk pohon dewasa karena menangkap asimtot tinggi biologis (tinggi maksimum). Secara default, sistem menggunakan koefisien regional Weibull 3-parameter Feldpausch untuk Asia Tenggara ($a=57.122, b=0.0332, c=0.8468$). Pengguna dapat mengesampingkan ini dengan koefisien spesifik spesies melalui `seed_species.csv`.

Seiring waktu, tinggi tumbuh sebagai fungsi dari DBH yang diprakirakan, menghitung kembali estimasi tinggi secara dinamis seiring berkembangnya pohon.

> **Status:** ✅ Akurasi tinggi. i-Tree Eco menggunakan kurva pertumbuhan tinggi spesifik spesies. Integrasi model Weibull Feldpausch memberikan akurasi yang sebanding untuk konteks tropis di mana kurva pertumbuhan lokal tidak tersedia.

---

## 11. Perbedaan dari i-Tree Eco

### Tabel perbandingan ringkasan

| Fitur | i-Tree Eco | i-Tree SEA | Dampak |
|:---|:---|:---|:---|
| Persamaan AGB | Spesifik spesies + Chave 2014 | Chave 2014 pantropis & Ketterings 2001 | Rendah — Menambahkan spesifik regional untuk Indonesia |
| Pembobotan berat jenis kayu | Rasio WD pasca-proses | $\rho$ langsung dalam persamaan | Tidak ada — setara secara fungsional |
| Tinggi pohon | Diukur di lapangan | Estimasi Weibull (Feldpausch 2012) | Rendah — Model Weibull menangkap asimtot tinggi tropis secara akurat |
| Laju pertumbuhan | Tabel lapangan/regional | Kategoris (lambat/sedang/cepat) | Rendah — sesuai untuk prakiraan |
| Penyesuaian perkotaan | Tergantung CLE (0.80) | Selalu 0.80 | Rendah — konservatif |
| Air hujan | Keseimbangan air per jam | Proksi tahunan + profil lokasi / unggah data per jam | Rendah — Mode Lanjutan menjalankan pembatasan kapasitas intersepsi kejadian per jam |
| Polusi udara | Model deposisi per jam | Proksi tahunan × pengali konsentrasi per jam/lokasi | Rendah — Mode Lanjutan menyesuaikan laju penyaringan dengan konsentrasi terukur |
| Kematian pohon | Ya (penyerapan bersih) | Tidak (hanya kotor/gross) | Sedang — penyerapan kotor adalah standar untuk rencana penanaman |
| Penghematan energi | Ya | Tidak | Di luar ruang lingkup |
| Ekuivalen CO₂ & O₂ | Ya | Ya (IPCC & Nowak 2007) | Tidak ada — metode stoikiometri identik |
| Ekuivalensi EPA | Tidak (hanya laporan spesifik AS) | Ya (Bensin, Jarak Mengemudi) | Tinggi — meningkatkan komunikasi publik |

---

## 12. Referensi

### Model alometrik utama

1. **Chave, J., et al. (2014).** "Improved allometric models to estimate the aboveground biomass of tropical trees." *Global Change Biology*, 20(10), 3177–3190. — Persamaan AGB Utama.
2. **Chave, J., et al. (2005).** "Tree allometry and improved estimation of carbon stocks and balance in tropical forests." *Oecologia*, 145, 87–99. — Persamaan karbon tropis spesifik iklim (i-Tree Eco v6.0.22).
3. **Cairns, M.A., et al. (1997).** "Root biomass allocation in the world's upland forests." *Oecologia*, 111, 1–11. — Rasio akar-ke-pucuk.
4. **Feldpausch, T.R., et al. (2012).** "Tree height integrated into pantropical forest biomass estimates." *Biogeosciences*, 9, 3381–3403. — Estimasi tinggi.

### Metode i-Tree

5. **Nowak, D.J. (2023).** "Understanding i-Tree: 2023 Summary of Programs and Methods." USDA Forest Service. — [PDF](https://www.itreetools.org/documents/1099/UnderstandingiTree2023.pdf)
6. **i-Tree (2021).** "New Carbon Equations and Methods." — [Halaman Web](https://www.itreetools.org/support/resources-overview/i-tree-methods-and-files/new-carbon-equations-and-methods-2020)
7. **i-Tree (2021).** "Tropical Carbon Equations." — [Halaman Web](https://www.itreetools.org/support/resources-overview/i-tree-methods-and-files/i-tree-eco-tropical-carbon-equations)
8. **i-Tree (2016).** "Pollutant Removal, Biogenic Emissions and Hydrologic Processes." — [PDF](http://www.itreetools.org/landscape/resources/Air_Pollutant_Removals_Biogenic_Emissions_and_Hydrologic_Estimates_for_iTree_v6_Applications.pdf)

### Berat jenis kayu & data spesies

9. **Chave, J., et al. (2009).** "Towards a worldwide wood economics spectrum." *Ecology Letters*, 12(4), 351–366.
10. **Zanne, A.E., et al. (2009).** "Global Wood Density Database." *Dryad Digital Repository*.
11. **McPherson, E.G., et al. (2016).** "Urban Tree Database and Allometric Equations." Gen. Tech. Rep. PSW-GTR-235, USDA FS.

### Hidrologi & polusi

12. **Wang, J., et al. (2008).** "A Numerical Model for Flow and Pollution Transport in a 2D Urban Stormwater Drainage System." — Landasan i-Tree Hydro.
13. **Hirabayashi, S. (2013).** "i-Tree Eco Precipitation Interception Model." — Model intersepsi curah hujan terupdate.
14. **Nowak, D.J., et al. (2006).** "Air pollution removal by urban trees and shrubs in the United States." *Urban Forestry & Urban Greening*, 4(3–4), 115–123.

### Pertumbuhan & kehutanan perkotaan

15. **Nowak, D.J. (1994).** "Atmospheric Carbon Dioxide Reduction by Chicago's Urban Forest." — Faktor penyesuaian perkotaan.
16. **Pretzsch, H. (2009).** "Forest Dynamics, Growth and Yield." Springer. — Kalibrasi laju pertumbuhan.
17. **Asner, G.P., et al. (2003).** "Global synthesis of leaf area index observations." *Global Ecology and Biogeography*, 12, 191–205. — Default LAI.
18. **Peper, P.J., et al. (2001).** "Tree size facts." Center for Urban Forest Research, USDA FS. — Estimasi lebar tajuk.
19. **Ketterings, Q.M., et al. (2001).** "Reducing uncertainty in the use of allometric biomass equations for predicting above-ground tree biomass in mixed secondary forests." *Forest Ecology and Management*, 146(1-3), 199-209.
20. **Nowak, D.J., et al. (2007).** "Oxygen production by urban trees in the United States." *Arboriculture & Urban Forestry*.
21. **US Environmental Protection Agency (EPA).** "Greenhouse Gas Equivalencies Calculator."

---

## Lampiran A: Referensi Konstanta

| Konstanta | Nilai | Satuan | Sumber |
|:---|:---|:---|:---|
| CHAVE_A | 0.0673 | — | Chave 2014 |
| CHAVE_B | 0.976 | — | Chave 2014 |
| BIOCLIMATIC_E | -0.070 | — | Chave 2014, Table S3 |
| ROOT_SHOOT_RATIO | 0.26 | — | Cairns 1997 |
| URBAN_ADJUSTMENT | 0.80 | — | Nowak 1994 |
| CARBON_FRACTION | 0.50 / 0.41 (palem) | — | IPCC 2006 |
| CARBON_STORAGE_CAP | 7.500 | kg C | i-Tree Eco |
| SEQUESTRATION_RATE_CAP | 40 | kg C/cm | i-Tree Eco |
| DEFAULT_WOOD_DENSITY | 0.58 | g/cm³ | Chave 2009 |
| DEFAULT_LAI | 5.0 | m²/m² | Asner 2003 |
| SPECIFIC_LEAF_STORAGE | 0.0002 | m | Wang 2008 |
| ANNUAL_RAIN_EVENTS | 180 | kejadian/tahun | Singapore Met |
| CW_INTERCEPT | 0.6 | m | Peper 2001 |
| CW_SLOPE | 0.15 | m/cm | Peper 2001 |
| CW_MAX | 20.0 | m | Dibatasi |
| HEIGHT_A | 0.893 | — | Feldpausch 2012 |
| HEIGHT_B | 0.760 | — | Feldpausch 2012 |
