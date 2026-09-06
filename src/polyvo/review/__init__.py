"""
Katman 4 — INSAN DUZELTME YOLU.

Modelin yazdigini insanin duzeltmesi icin iki yon: `export` odenmis depodan
duzeltilebilir satirlari cikarir, `import` duzeltilmis dosyayi geri yazar ve
ayni satiri `data/human/` altina YEDEKLER (depo silinse de emek kaybolmaz).

Bu katman hicbir sey URETMEZ, hicbir LLM cagrisi yapmaz, KIMLIK TAHSIS ETMEZ:
depoda karsiligi olmayan bir anahtar duzeltilemez — `curriculum` disinda
ikinci bir kimlik ureteci yoktur.
"""
