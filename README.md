# Restoran Takip

Otel restoranı için kamera görüntüsünden **masa doluluğu** ve **büfe kuyruğu** takibi yapan masaüstü uygulaması.
YOLOv8 ile kişileri tespit eder, çizilen bölgelerde sayar, sonuçları **SQL Server**'a yazar.

## Özellikler

- **Canlı Masalar:** Video/kamera üzerinde masalar dolu (kırmızı) / boş (yeşil) görünür, `Boş masa: X / Y` özeti verilir.
- **Dolu/boş mantığı:** Masada kişi belirli süre kesintisiz varsa DOLU, belirli süre kesintisiz yoksa BOŞ sayılır. Kısa süreli tespit kaçırmaları ya da yoldan geçen garsonlar durumu bozmaz.
- **Büfe yoğunluğu:** `masa` ile başlamayan alanlar (örn. `bufe`) kuyruk alanı sayılır, eşik aşılınca YOĞUN işaretlenir.
- **Bölgeler:** Masalar fareyle poligon olarak çizilir ve `zones.json` dosyasına kaydedilir.
- **Raporlar:** Anlık masa durumu, masa/alan özeti, saat bazlı yoğunluk, son durum değişiklikleri.
- **Ayarlar:** Video/kamera kaynağı, SQL bağlantısı, süre ve eşik değerleri arayüzden değiştirilir.
- SQL bağlantısı kopsa bile sayım devam eder, bağlantı 15 sn'de bir yeniden denenir.

## Kurulum

Gereksinimler: Python 3.10+, SQL Server (Express yeterli), Windows için "ODBC Driver 17 veya 18 for SQL Server".

```bash
pip install -r requirements.txt
```

1. SQL Server'da `sql/kurulum.sql` dosyasını çalıştır (veritabanı ve tabloları oluşturur).
2. Test videonu `data/restoran.mp4` olarak koy (ya da Ayarlar'dan başka bir video/kamera seç).
3. Uygulamayı başlat:

```bash
python app.py
```

4. **Ayarlar** sayfasında SQL sunucu adını gir, "Bağlantıyı Test Et"e bas, **Kaydet**.
5. **Bölgeler** sayfasında masaları çiz (`masa1`, `masa2`, ... adlarıyla), gerekirse büfe için `bufe` alanı ekle.
6. **Canlı Masalar** sayfasında **Başlat**.

YOLO modeli (`yolov8n.pt`) ilk çalıştırmada `ultralytics` tarafından otomatik indirilir.

## Bölge adlandırma

- Adı `masa` ile başlayan bölgeler masa olarak ele alınır (dolu/boş takibi yapılır).
- Diğer bölgeler (örn. `bufe`) kuyruk alanıdır, sadece kişi sayısı ve yoğunluk takip edilir.
- Adlarda yalnızca İngilizce harf, rakam ve `_` kullan.

## Veritabanı

| Tablo | İçerik |
|---|---|
| `BolgeSayim` | Her yazma aralığında her bölgedeki kişi sayısı |
| `MasaDurum` | Masanın Dolu/Bos durumu değiştiği anlar |

## Proje yapısı

```
app.py        Arayüz (PySide6)
worker.py     Video okuma, YOLO tespiti, dolu/boş mantığı
db.py         SQL Server işlemleri ve rapor sorguları
config.py     Ayarlar ve zones.json işlemleri
sql/          Veritabanı kurulum betiği
data/         Videolar (repoya dahil edilmez)
```

`settings.json` ve `zones.json` ilk kullanımda oluşur. `settings.json` SQL bilgilerini içerebildiği için repoya dahil edilmez.

## Notlar

- **Gizlilik:** Gerçek kamera görüntüsü kişisel veri içerir. Kullanımdan önce KVKK yükümlülüklerini kontrol et. Uygulama görüntü kaydetmez, sadece kişi sayısını yazar.
- **Garson/personel** da "kişi" olarak sayılır. Süre eşikleri bunu büyük ölçüde azaltır.
- **Lisans:** Proje [Ultralytics](https://github.com/ultralytics/ultralytics) (AGPL-3.0) kullanır. Dağıtım veya ticari kullanımdan önce lisans koşullarını kontrol et.
