"""Ayarlar ve bölge dosyası (zones.json) işlemleri."""
import json
import re
import sys
from pathlib import Path

if getattr(sys, "frozen", False):          # .exe olarak çalışıyorsa
    BASE = Path(sys.executable).parent
else:
    BASE = Path(__file__).resolve().parent

AYAR_DOSYASI = BASE / "settings.json"

VARSAYILAN = {
    "kaynak": "data/restoran.mp4",   # video yolu, kamera için 0, IP kamera için rtsp://...
    "video_tekrar": True,            # video bitince başa sar
    "model": "yolov8n.pt",
    "guven": 0.25,                   # YOLO güven eşiği
    "bolge_dosyasi": "zones.json",
    "sql_sunucu": "localhost\\SQLEXPRESS",
    "sql_veritabani": "RestoranDB",
    "sql_driver": "ODBC Driver 17 for SQL Server",
    "sql_windows_auth": True,
    "sql_kullanici": "",
    "sql_sifre": "",
    "yazma_araligi": 5,              # saniye
    "dolu_suresi": 10,               # masada kişi bu kadar sn kesintisiz varsa DOLU
    "bos_suresi": 10,                # masada kişi bu kadar sn kesintisiz yoksa BOŞ
    "yogun_esigi": 5,                # büfe/alan bu kişi sayısına ulaşınca YOĞUN
}


def ayarlari_yukle():
    ayar = dict(VARSAYILAN)
    if AYAR_DOSYASI.exists():
        try:
            with open(AYAR_DOSYASI, encoding="utf-8") as f:
                ayar.update(json.load(f))
        except (OSError, ValueError):
            pass
    return ayar


def ayarlari_kaydet(ayar):
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(ayar, f, indent=2, ensure_ascii=False)


def yol(p):
    """Göreli yolları uygulama klasörüne göre çözer."""
    p = Path(p)
    return p if p.is_absolute() else BASE / p


def kaynak_coz(kaynak):
    k = str(kaynak).strip()
    if k.isdigit():
        return int(k)          # kamera numarası
    if "://" in k:
        return k               # rtsp:// http:// vb.
    return str(yol(k))


def kaynak_dosya_mi(kaynak):
    return isinstance(kaynak, str) and "://" not in kaynak


def masa_mi(ad):
    return ad.lower().startswith("masa")


def dogal_sira(ad):
    return [int(s) if s.isdigit() else s.lower() for s in re.split(r"(\d+)", ad)]


def sirali_adlar(bolgeler):
    """Önce masalar (masa1, masa2, ... masa10), sonra diğer alanlar."""
    masalar = sorted([a for a in bolgeler if masa_mi(a)], key=dogal_sira)
    digerleri = sorted([a for a in bolgeler if not masa_mi(a)], key=dogal_sira)
    return masalar + digerleri


def bolgeleri_yukle(dosya):
    p = yol(dosya)
    if not p.exists():
        return {}
    try:
        with open(p, encoding="utf-8") as f:
            veri = json.load(f)
        return {ad: [[int(x), int(y)] for x, y in pts] for ad, pts in veri.items()}
    except (OSError, ValueError, TypeError):
        return {}


def bolgeleri_kaydet(dosya, bolgeler):
    with open(yol(dosya), "w", encoding="utf-8") as f:
        json.dump(bolgeler, f, indent=2)
