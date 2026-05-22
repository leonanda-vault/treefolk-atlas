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

## 5. Intersepsi Air Hujan

Aplikasi ini menggunakan proksi tahunan untuk memperkirakan volume air hujan yang diintersepsi oleh kanopi pohon:

$$\text{Intersepsi Tahunan (L)} = \text{Luas Tajuk} \times \text{LAI} \times S_L \times N_{\text{events}} \times 1000$$

| Parameter | Arti / Nilai | Sumber / Keterangan |
| :--- | :--- | :--- |
| Luas Tajuk | $\pi \times (\text{CW}/2)^2$ | $\text{CW} = 0.6 + 0.15 \times \text{DBH}$ (maks 20m) |
| LAI | 5.0 (default) | Indeks Area Daun untuk daun lebar tropis |
| $S_L$ | 0.0002 m (0.2 mm) | Kapasitas penyimpanan air per unit area daun |
| $N_{\text{events}}$ | 180 kejadian hujan/tahun | Data rata-rata regional |

---

## 6. Penyaringan Polusi Udara

Penyaringan polusi udara dihitung berdasarkan total luas area daun (Leaf Area Index) dan laju deposisi kering polutan udara sekitar (PM2.5, $\text{NO}_2$, $\text{O}_3$, dan $\text{SO}_2$). Laju deposisi disesuaikan menggunakan **Pengali Polusi** dari Profil Lokasi untuk mencerminkan konsentrasi polutan aktual di perkotaan Asia Tenggara.
