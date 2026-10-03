"""Arka planda video okuyup YOLO ile sayım yapan iş parçacığı."""
import time
from datetime import datetime

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

import config
from db import Veritabani

# BGR renkler
MASA_DOLU = (60, 60, 230)
MASA_BOS = (80, 190, 80)
ALAN_NORMAL = (230, 170, 50)
ALAN_YOGUN = (0, 140, 255)


class MasaDurumu:
    """Dolu/boş geçişi: durum ancak yeterince uzun süre değişmeyen gözlemle değişir."""

    def __init__(self, dolu_s, bos_s):
        self.dolu = False
        self.dolu_s = dolu_s
        self.bos_s = bos_s
        self.aday_t = None

    def guncelle(self, kisi_var, t):
        """Durum değiştiyse True döner."""
        if kisi_var == self.dolu:
            self.aday_t = None
            return False
        if self.aday_t is None:
            self.aday_t = t
        esik = self.dolu_s if kisi_var else self.bos_s
        if t - self.aday_t >= esik:
            self.dolu = kisi_var
            self.aday_t = None
            return True
        return False


def bgr_to_qimage(bgr):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, _ = rgb.shape
    return QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy()


def yazi_ciz(kare, metin, merkez, olcek, kalin):
    (tw, th), _ = cv2.getTextSize(metin, cv2.FONT_HERSHEY_SIMPLEX, olcek, kalin)
    org = (int(merkez[0] - tw / 2), int(merkez[1] + th / 2))
    cv2.putText(kare, metin, org, cv2.FONT_HERSHEY_SIMPLEX, olcek, (0, 0, 0), kalin + 3)
    cv2.putText(kare, metin, org, cv2.FONT_HERSHEY_SIMPLEX, olcek, (255, 255, 255), kalin)


def ciz(kare, bolgeler, bilgi, kutular):
    h, w = kare.shape[:2]
    olcek = max(0.6, w / 1920)
    kalin = max(1, int(2 * olcek))

    kat = kare.copy()
    for ad, p in bolgeler.items():
        cv2.fillPoly(kat, [p], bilgi[ad]["renk"])
    cv2.addWeighted(kat, 0.25, kare, 0.75, 0, kare)

    for x1, y1, x2, y2, ayak, icinde in kutular:
        renk = (255, 255, 255) if icinde else (150, 150, 150)
        cv2.rectangle(kare, (x1, y1), (x2, y2), renk, kalin)
        cv2.circle(kare, ayak, max(3, int(5 * olcek)), renk, -1)

    for ad, p in bolgeler.items():
        cv2.polylines(kare, [p], True, bilgi[ad]["renk"], max(2, int(3 * olcek)))
        merkez = p.mean(axis=0)
        yazi_ciz(kare, f"{ad}: {bilgi[ad]['kisi']}", merkez, 0.9 * olcek, kalin + 1)


class SayimIsci(QThread):
    kare = Signal(QImage)
    durum = Signal(dict)          # {ad: {"tip","kisi","durum"}}
    db_durum = Signal(bool, str)
    hata = Signal(str)
    bilgi = Signal(str)

    def __init__(self, ayar):
        super().__init__()
        self.a = ayar
        self._dur = False
        self.db = Veritabani(ayar)
        self.db_ok = False
        self._son_deneme = 0.0
        self._ilk_yazildi = False
        self.bekleyen = []

    def durdur(self):
        self._dur = True

    # ---- veritabanı ----
    def _db_dene(self, durumlar):
        simdi = time.time()
        if simdi - self._son_deneme < 15:
            return False
        self._son_deneme = simdi
        try:
            self.db.kapat()
            self.db.baglan()
            self.db.sema_olustur()
        except Exception as e:
            self.db_ok = False
            self.db_durum.emit(False, str(e))
            return False
        self.db_ok = True
        self.db_durum.emit(True, "")
        if not self._ilk_yazildi:
            self._ilk_yazildi = True
            for ad, d in durumlar.items():
                self.bekleyen.append((datetime.now(), ad, "Dolu" if d.dolu else "Bos"))
        return True

    def _db_yaz(self, sayim, durumlar):
        if not self.db_ok and not self._db_dene(durumlar):
            return
        try:
            self.db.sayim_yaz(list(sayim.items()))
            if self.bekleyen:
                self.db.durum_yaz(self.bekleyen)
                self.bekleyen = []
        except Exception as e:
            self.db_ok = False
            self.db_durum.emit(False, str(e))
            self.db.kapat()
            self.bekleyen = self.bekleyen[-5000:]

    # ---- ana döngü ----
    def run(self):
        a = self.a
        cap = None
        try:
            try:
                from ultralytics import YOLO
                model = YOLO(str(config.yol(a["model"])))
            except Exception as e:
                self.hata.emit(f"Model yüklenemedi: {e}")
                return

            ham = config.bolgeleri_yukle(a["bolge_dosyasi"])
            if not ham:
                self.hata.emit("Hiç bölge yok. Önce 'Bölgeler' sayfasından masaları çiz.")
                return
            bolgeler = {ad: np.array(ham[ad], dtype=np.int32)
                        for ad in config.sirali_adlar(ham)}
            durumlar = {ad: MasaDurumu(a["dolu_suresi"], a["bos_suresi"])
                        for ad in bolgeler if config.masa_mi(ad)}

            kaynak = config.kaynak_coz(a["kaynak"])
            dosya = config.kaynak_dosya_mi(kaynak)
            cap = cv2.VideoCapture(kaynak)
            if not cap.isOpened():
                self.hata.emit(f"Kaynak açılamadı: {a['kaynak']}")
                return
            fps = cap.get(cv2.CAP_PROP_FPS)
            if not fps or fps != fps or fps < 1:
                fps = 25.0

            sim_t = 0.0
            son_yazma = 0.0
            son_emit = 0.0
            basa_sardi = False

            while not self._dur:
                ok, kare = cap.read()
                if not ok:
                    if dosya and a["video_tekrar"] and not basa_sardi:
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        basa_sardi = True
                        continue
                    self.bilgi.emit("Video bitti." if dosya else "Kamera görüntüsü alınamadı.")
                    break
                basa_sardi = False

                t = sim_t if dosya else time.time()
                sim_t += 1.0 / fps

                sonuc = model(kare, classes=[0], conf=a["guven"], verbose=False)[0]
                sayim = {ad: 0 for ad in bolgeler}
                kutular = []
                for x1, y1, x2, y2 in sonuc.boxes.xyxy.tolist():
                    ayak = (int((x1 + x2) / 2), int(y2))     # kutunun alt orta noktası
                    icinde = False
                    for ad, p in bolgeler.items():
                        if cv2.pointPolygonTest(p, ayak, False) >= 0:
                            sayim[ad] += 1
                            icinde = True
                    kutular.append((int(x1), int(y1), int(x2), int(y2), ayak, icinde))

                bilgi = {}
                for ad in bolgeler:
                    n = sayim[ad]
                    if ad in durumlar:
                        if durumlar[ad].guncelle(n > 0, t):
                            self.bekleyen.append(
                                (datetime.now(), ad, "Dolu" if durumlar[ad].dolu else "Bos"))
                        dolu = durumlar[ad].dolu
                        bilgi[ad] = {"tip": "masa", "kisi": n,
                                     "durum": "Dolu" if dolu else "Bos",
                                     "renk": MASA_DOLU if dolu else MASA_BOS}
                    else:
                        yogun = n >= a["yogun_esigi"]
                        bilgi[ad] = {"tip": "alan", "kisi": n,
                                     "durum": "Yogun" if yogun else "Normal",
                                     "renk": ALAN_YOGUN if yogun else ALAN_NORMAL}

                simdi = time.time()
                if simdi - son_yazma >= a["yazma_araligi"]:
                    son_yazma = simdi
                    self._db_yaz(sayim, durumlar)

                if simdi - son_emit >= 0.2:
                    son_emit = simdi
                    ciz(kare, bolgeler, bilgi, kutular)
                    if kare.shape[1] > 1100:
                        o = 1100 / kare.shape[1]
                        kare = cv2.resize(kare, None, fx=o, fy=o)
                    self.kare.emit(bgr_to_qimage(kare))
                    self.durum.emit({ad: {k: v for k, v in b.items() if k != "renk"}
                                     for ad, b in bilgi.items()})

            # çıkışta bekleyen durum değişikliklerini yazmayı dene
            if self.db_ok and self.bekleyen:
                try:
                    self.db.durum_yaz(self.bekleyen)
                except Exception:
                    pass
        except Exception as e:
            self.hata.emit(f"Beklenmeyen hata: {e}")
        finally:
            if cap is not None:
                cap.release()
            self.db.kapat()
