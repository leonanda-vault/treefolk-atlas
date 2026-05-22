import os
import sys

csv_path = r"D:\Leonanda's Professional Vault\Projects\itree-sea\data\seed_species.csv"

# Append to CSV
new_csv_lines = [
    "PDMC,Lohansung,Podocarpus macrophyllus,Podocarpus,Podocarpaceae,slow,0,indonesia,Ornamental conifer,0.45,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "PLOB,Balibong,Palaquium obovatum,Palaquium,Sapotaceae,slow,0,indonesia,Ornamental exotic trunk,0.60,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "DDAS,Bambu Petung,Dendrocalamus asper,Dendrocalamus,Poaceae,fast,1,indonesia,Giant bamboo,0.60,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "CSEQ,Cemara Angin,Casuarina equisetifolia,Casuarina,Casuarinaceae,fast,0,indonesia,Coastal conifer,0.80,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "AGDM,Damar,Agathis dammara,Agathis,Araucariaceae,moderate,0,indonesia,Resin-producing conifer,0.45,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "SZJM,Jambu Mawar,Syzygium jambos,Syzygium,Myrtaceae,moderate,0,indonesia,Rose apple,0.60,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "MLCJ,Kayu Putih,Melaleuca cajuputi,Melaleuca,Myrtaceae,moderate,0,indonesia,Cajuput tree,0.75,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "MROL,Kelor Africa,Moringa oleifera,Moringa,Moringaceae,fast,0,indonesia,Drumstick tree,0.30,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "TRMN,Ketapang Mini,Terminalia mantaly,Terminalia,Combretaceae,moderate,0,indonesia,Umbrella tree,0.60,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "SLBB,Liang Liu,Salix babylonica,Salix,Salicaceae,fast,0,indonesia,Weeping willow,0.40,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "SZPR,Pakis Brazil,Schizolobium parahyba,Schizolobium,Fabaceae,fast,0,indonesia,Brazilian firetree,0.30,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD",
    "HIMP,Tabebuia Pink,Handroanthus impetiginosus,Handroanthus,Bignoniaceae,moderate,0,indonesia,Pink trumpet tree,0.80,chave_2014,0.0673,0.976,,0.893,0.760,Chave 2014; ICRAF WD"
]

with open(csv_path, "a", encoding="utf-8") as f:
    f.write("\n")
    f.write("\n".join(new_csv_lines))

print("Added 12 species to seed_species.csv")
