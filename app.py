"""Restoran Takip - masaüstü uygulaması (PySide6)."""
import re
import sys
from datetime import datetime

import cv2
from PySide6.QtCore import QPointF, QRectF, Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import (
    QAbstractItemView, QApplication, QCheckBox, QComboBox, QDoubleSpinBox,
    QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QSizePolicy, QSpinBox, QStackedWidget, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget, QScrollArea,
)

import config
import db
from worker import SayimIsci

GUNLER = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz",
         "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
BASLIKLAR = ["Ana Sayfa", "Canlı Masalar", "Bölgeler", "Raporlar", "Ayarlar"]
RENKLER = [(255, 200, 0), (0, 220, 255), (255, 90, 255), (255, 150, 0),
           (120, 160, 255), (100, 255, 120), (255, 120, 180), (0, 220, 170)]

STIL = """
* { font-family: 'Segoe UI', 'Noto Sans', sans-serif; }
#kok { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #a8286f, stop:0.45 #5a2a7e, stop:1 #2b1a5c); }
QLabel { color: white; font-size: 14px; }
#ustbar { background: rgba(0, 0, 0, 80); }
#baslik { font-size: 20px; font-weight: 600; }
#chip { font-size: 13px; }
#saat { font-size: 84px; font-weight: 700; }
#tarih { font-size: 22px; }
#tile { background: #26164a; border-radius: 20px; }
#tile:hover { background: #3a2270; }
#tile_simge { font-size: 60px; }
#tile_metin { font-size: 20px; font-weight: 600; }
#panel { background: rgba(20, 10, 50, 170); border-radius: 14px; }
#ozet { font-size: 30px; font-weight: 700; }
#video { background: #150c33; border-radius: 10px; color: #bbb; }
#uyari { color: #ffd166; }
QPushButton { background: #e5386d; color: white; border: none; border-radius: 8px;
              padding: 10px 18px; font-size: 14px; font-weight: 600; }
QPushButton:hover { background: #ff4d82; }
QPushButton:disabled { background: #4a4a5a; color: #999; }
QPushButton#ikincil { background: #3b2a73; }
QPushButton#ikincil:hover { background: #4d3894; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #1d1240; color: white; border: 1px solid #5b4a9a;
    border-radius: 6px; padding: 6px; font-size: 14px; }
QLineEdit:disabled { color: #888; }
QComboBox QAbstractItemView { background: #1d1240; color: white;
    selection-background-color: #e5386d; }
QCheckBox { color: white; font-size: 14px; }
QGroupBox { color: white; font-size: 15px; font-weight: 600; border: 1px solid #5b4a9a;
            border-radius: 10px; margin-top: 14px; padding-top: 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }
QListWidget { background: #1d1240; color: white; border: 1px solid #5b4a9a;
              border-radius: 6px; font-size: 14px; }
QListWidget::item:selected { background: #e5386d; }
QTableWidget { background: rgba(20, 10, 50, 150); color: white; border: none;
               gridline-color: #3b2a73; font-size: 14px; }
QHeaderView::section { background: #3b2a73; color: white; padding: 6px; border: none;
                       font-weight: 600; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #1d1240; width: 12px; }
QScrollBar::handle:vertical { background: #5b4a9a; border-radius: 5px; }
"""


class Is(QThread):
    """Küçük arka plan işi (SQL testi, rapor sorgusu)."""
    bitti = Signal(object)
    hata = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.bitti.emit(self.fn())
        except Exception as e:
            self.hata.emit(str(e))


class Tile(QFrame):
    tiklandi = Signal()

    def __init__(self, simge, metin):
        super().__init__()
        self.setObjectName("tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumSize(200, 190)
        lay = QVBoxLayout(self)
        lay.addStretch()
        s = QLabel(simge)
        s.setObjectName("tile_simge")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t = QLabel(metin)
        t.setObjectName("tile_metin")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(s)
        lay.addWidget(t)
        lay.addStretch()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.tiklandi.emit()


# ------------------------------------------------------------------ ANA SAYFA
class AnaSayfa(QWidget):
    git = Signal(int)

    def __init__(self):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(50, 30, 50, 30)
        lay.setSpacing(40)

        sol = QVBoxLayout()
        sol.addStretch()
        self.tarih = QLabel()
        self.tarih.setObjectName("tarih")
        self.saat = QLabel()
        self.saat.setObjectName("saat")
        sol.addWidget(self.tarih)
        sol.addWidget(self.saat)
        sol.addStretch()
        lay.addLayout(sol, 2)

        izgara = QGridLayout()
        izgara.setSpacing(18)
        kutular = [("🍽", "Canlı Masalar", 1), ("✏️", "Bölgeler", 2),
                   ("📊", "Raporlar", 3), ("⚙️", "Ayarlar", 4)]
        for i, (simge, metin, idx) in enumerate(kutular):
            t = Tile(simge, metin)
            t.tiklandi.connect(lambda idx=idx: self.git.emit(idx))
            izgara.addWidget(t, i // 2, i % 2)
        lay.addLayout(izgara, 3)
        self.saati_guncelle()

    def saati_guncelle(self):
        n = datetime.now()
        self.tarih.setText(f"{n.day} {AYLAR[n.month - 1]} {GUNLER[n.weekday()]}")
        self.saat.setText(n.strftime("%H:%M"))


# ------------------------------------------------------------- CANLI MASALAR
class CanliSayfa(QWidget):
    baslat = Signal()
    durdur = Signal()

    DURUM_METIN = {"Dolu": "DOLU", "Bos": "BOŞ", "Yogun": "YOĞUN", "Normal": "NORMAL"}
    DURUM_RENK = {"Dolu": "#c0392b", "Bos": "#1e8449", "Yogun": "#d35400", "Normal": "#2874a6"}

    def __init__(self):
        super().__init__()
        ana = QHBoxLayout(self)
        ana.setContentsMargins(20, 20, 20, 20)
        ana.setSpacing(16)

        sol = QVBoxLayout()
        self.video = QLabel("Başlat'a basınca canlı görüntü burada görünür.")
        self.video.setObjectName("video")
        self.video.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video.setMinimumSize(640, 360)
        self.video.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        sol.addWidget(self.video, 1)

        alt = QHBoxLayout()
        self.btn_baslat = QPushButton("▶  Başlat")
        self.btn_durdur = QPushButton("■  Durdur")
        self.btn_durdur.setObjectName("ikincil")
        self.btn_durdur.setEnabled(False)
        self.btn_baslat.clicked.connect(self.baslat)
        self.btn_durdur.clicked.connect(self.durdur)
        self.mesaj = QLabel("")
        self.mesaj.setObjectName("uyari")
        self.mesaj.setWordWrap(True)
        alt.addWidget(self.btn_baslat)
        alt.addWidget(self.btn_durdur)
        alt.addWidget(self.mesaj, 1)
        sol.addLayout(alt)
        ana.addLayout(sol, 3)

        panel = QFrame()
        panel.setObjectName("panel")
        panel.setMinimumWidth(340)
        panel.setMaximumWidth(420)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 16, 16, 16)
        self.ozet = QLabel("Boş masa: - / -")
        self.ozet.setObjectName("ozet")
        pl.addWidget(self.ozet)
        self.tablo = QTableWidget(0, 3)
        self.tablo.setHorizontalHeaderLabels(["Alan", "Durum", "Kişi"])
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        pl.addWidget(self.tablo, 1)
        ana.addWidget(panel, 1)

    def calisiyor(self, evet):
        self.btn_baslat.setEnabled(not evet)
        self.btn_durdur.setEnabled(evet)

    def kare_goster(self, img):
        pm = QPixmap.fromImage(img).scaled(
            self.video.size(), Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation)
        self.video.setPixmap(pm)

    def temizle(self):
        self.video.clear()
        self.video.setText("Başlat'a basınca canlı görüntü burada görünür.")

    def durum_guncelle(self, durum):
        adlar = list(durum.keys())
        if self.tablo.rowCount() != len(adlar):
            self.tablo.setRowCount(len(adlar))
        masalar = [a for a, d in durum.items() if d["tip"] == "masa"]
        bos = sum(1 for a in masalar if durum[a]["durum"] == "Bos")
        self.ozet.setText(f"Boş masa: {bos} / {len(masalar)}")
        for r, ad in enumerate(adlar):
            d = durum[ad]
            hucreler = [ad, self.DURUM_METIN[d["durum"]], str(d["kisi"])]
            for c, metin in enumerate(hucreler):
                it = self.tablo.item(r, c)
                if it is None:
                    it = QTableWidgetItem()
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self.tablo.setItem(r, c, it)
                it.setText(metin)
                if c == 1:
                    it.setBackground(QColor(self.DURUM_RENK[d["durum"]]))


# ------------------------------------------------------------------ BÖLGELER
class KareCanvas(QWidget):
    degisti = Signal()

    def __init__(self):
        super().__init__()
        self.setMinimumSize(640, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.kare = None
        self.bolgeler = {}
        self.noktalar = []
        self.secili = None

    def kare_ayarla(self, img):
        self.kare = img
        self.update()

    def _yerlesim(self):
        iw, ih = self.kare.width(), self.kare.height()
        s = min(self.width() / iw, self.height() / ih)
        return s, (self.width() - iw * s) / 2, (self.height() - ih * s) / 2

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#150c33"))
        if self.kare is None:
            p.setPen(QColor("white"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Görüntü yok. Ayarlar'dan kaynağı seç, sonra 'Kareyi Yenile'ye bas.")
            return
        s, ox, oy = self._yerlesim()
        iw, ih = self.kare.width(), self.kare.height()
        p.drawImage(QRectF(ox, oy, iw * s, ih * s), self.kare)

        for i, (ad, pts) in enumerate(self.bolgeler.items()):
            r, g, b = RENKLER[i % len(RENKLER)]
            renk = QColor(r, g, b)
            sec = ad == self.secili
            p.setPen(QPen(renk, 4 if sec else 2))
            p.setBrush(QColor(r, g, b, 70 if sec else 30))
            p.drawPolygon(QPolygonF([QPointF(ox + x * s, oy + y * s) for x, y in pts]))
            p.setPen(renk)
            p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
            p.drawText(QPointF(ox + pts[0][0] * s + 6, oy + pts[0][1] * s + 20), ad)

        if self.noktalar:
            q = [QPointF(ox + x * s, oy + y * s) for x, y in self.noktalar]
            p.setPen(QPen(QColor("#2ecc71"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            if len(q) >= 3:
                p.drawPolygon(QPolygonF(q))
            elif len(q) == 2:
                p.drawLine(q[0], q[1])
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#e74c3c"))
            for pt in q:
                p.drawEllipse(pt, 5, 5)

    def mousePressEvent(self, e):
        if self.kare is None:
            return
        s, ox, oy = self._yerlesim()
        x = (e.position().x() - ox) / s
        y = (e.position().y() - oy) / s
        if e.button() == Qt.MouseButton.LeftButton:
            if 0 <= x < self.kare.width() and 0 <= y < self.kare.height():
                self.noktalar.append((int(x), int(y)))
        elif e.button() == Qt.MouseButton.RightButton and self.noktalar:
            self.noktalar.pop()
        self.degisti.emit()
        self.update()


class BolgeSayfa(QWidget):
    def __init__(self, ayar_getir):
        super().__init__()
        self.ayar_getir = ayar_getir
        self.bolgeler = {}
        self.kaynak_imza = None

        ana = QHBoxLayout(self)
        ana.setContentsMargins(20, 20, 20, 20)
        ana.setSpacing(16)

        self.canvas = KareCanvas()
        ana.addWidget(self.canvas, 3)

        panel = QFrame()
        panel.setObjectName("panel")
        panel.setFixedWidth(330)
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(16, 16, 16, 16)
        info = QLabel("Sol tık: nokta ekle\nSağ tık: son noktayı geri al\n"
                      "En az 3 nokta koy, ad yaz, kaydet.\n"
                      "Masayı çizerken oturanların ayaklarını da içine al.")
        info.setWordWrap(True)
        pl.addWidget(info)
        pl.addWidget(QLabel("Kayıtlı bölgeler:"))
        self.liste = QListWidget()
        self.liste.currentTextChanged.connect(self._secildi)
        pl.addWidget(self.liste, 1)

        self.ad_kutu = QLineEdit()
        self.ad_kutu.setPlaceholderText("Bölge adı (örn: masa1)")
        pl.addWidget(self.ad_kutu)

        def dugme(metin, fn, ikincil=False):
            b = QPushButton(metin)
            if ikincil:
                b.setObjectName("ikincil")
            b.clicked.connect(fn)
            pl.addWidget(b)
            return b

        dugme("➕  Bölgeyi Kaydet", self.kaydet)
        dugme("↩  Son Noktayı Geri Al", self.geri_al, True)
        dugme("🧹  Çizimi Temizle", self.temizle, True)
        dugme("🗑  Seçili Bölgeyi Sil", self.sil, True)
        dugme("🔄  Kareyi Yenile", self.kare_yenile, True)
        self.bilgi = QLabel("")
        self.bilgi.setObjectName("uyari")
        self.bilgi.setWordWrap(True)
        pl.addWidget(self.bilgi)
        ana.addWidget(panel)

    # --- veri ---
    def hazirla(self):
        a = self.ayar_getir()
        self.bolgeler = config.bolgeleri_yukle(a["bolge_dosyasi"])
        self._listeyi_doldur()
        if self.canvas.kare is None or self.kaynak_imza != a["kaynak"]:
            self.kare_yenile()
        if not self.ad_kutu.text():
            self.ad_kutu.setText(self._onerilen_ad())

    def _listeyi_doldur(self):
        sirali = config.sirali_adlar(self.bolgeler)
        self.bolgeler = {ad: self.bolgeler[ad] for ad in sirali}
        self.canvas.bolgeler = self.bolgeler
        self.liste.blockSignals(True)
        self.liste.clear()
        self.liste.addItems(sirali)
        self.liste.blockSignals(False)
        self.canvas.secili = None
        self.canvas.update()

    def _onerilen_ad(self):
        n = sum(1 for k in self.bolgeler if config.masa_mi(k)) + 1
        while f"masa{n}" in self.bolgeler:
            n += 1
        return f"masa{n}"

    def _kaydet_dosya(self):
        config.bolgeleri_kaydet(self.ayar_getir()["bolge_dosyasi"], self.bolgeler)

    def _secildi(self, ad):
        self.canvas.secili = ad or None
        self.canvas.update()

    # --- eylemler ---
    def kare_yenile(self):
        a = self.ayar_getir()
        cap = cv2.VideoCapture(config.kaynak_coz(a["kaynak"]))
        ok, kare = cap.read()
        cap.release()
        if not ok:
            self.bilgi.setText(f"Kare okunamadı: {a['kaynak']}\n"
                               "Canlı izleme açıksa kamera kaynağı meşgul olabilir.")
            return
        rgb = cv2.cvtColor(kare, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        self.canvas.kare_ayarla(
            QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888).copy())
        self.kaynak_imza = a["kaynak"]
        self.bilgi.setText(f"Kare boyutu: {w}x{h}")

    def kaydet(self):
        ad = self.ad_kutu.text().strip()
        if not re.fullmatch(r"[A-Za-z0-9_]+", ad):
            QMessageBox.warning(self, "Geçersiz ad",
                                "Ad sadece İngilizce harf, rakam ve _ içerebilir (örn: masa1).")
            return
        if len(self.canvas.noktalar) < 3:
            QMessageBox.warning(self, "Eksik çizim", "En az 3 nokta koymalısın.")
            return
        if ad in self.bolgeler:
            c = QMessageBox.question(self, "Üzerine yaz",
                                     f"'{ad}' zaten var. Üzerine yazılsın mı?")
            if c != QMessageBox.StandardButton.Yes:
                return
        self.bolgeler[ad] = [list(p) for p in self.canvas.noktalar]
        self._kaydet_dosya()
        self.canvas.noktalar.clear()
        self._listeyi_doldur()
        self.ad_kutu.setText(self._onerilen_ad())
        self.bilgi.setText(f"'{ad}' kaydedildi. Çalışan sayım varsa yeniden başlatınca geçerli olur.")

    def sil(self):
        it = self.liste.currentItem()
        if not it:
            self.bilgi.setText("Önce listeden bir bölge seç.")
            return
        ad = it.text()
        c = QMessageBox.question(self, "Sil", f"'{ad}' silinsin mi?")
        if c == QMessageBox.StandardButton.Yes:
            del self.bolgeler[ad]
            self._kaydet_dosya()
            self._listeyi_doldur()
            self.ad_kutu.setText(self._onerilen_ad())

    def geri_al(self):
        if self.canvas.noktalar:
            self.canvas.noktalar.pop()
            self.canvas.update()

    def temizle(self):
        self.canvas.noktalar.clear()
        self.canvas.update()


# ------------------------------------------------------------------ RAPORLAR
class RaporSayfa(QWidget):
    def __init__(self, ayar_getir, arka_plan):
        super().__init__()
        self.ayar_getir = ayar_getir
        self.arka_plan = arka_plan
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        ust = QHBoxLayout()
        for ad in db.RAPORLAR:
            b = QPushButton(ad)
            b.setObjectName("ikincil")
            b.clicked.connect(lambda _=False, ad=ad: self.calistir(ad))
            ust.addWidget(b)
        ust.addStretch()
        lay.addLayout(ust)
        self.durum = QLabel("Bir rapor seç.")
        lay.addWidget(self.durum)
        self.tablo = QTableWidget()
        self.tablo.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tablo.verticalHeader().setVisible(False)
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        lay.addWidget(self.tablo, 1)

    def calistir(self, ad):
        self.durum.setText(f"'{ad}' çalışıyor...")
        veri = db.Veritabani(self.ayar_getir())
        sql = db.RAPORLAR[ad]
        self._ad = ad
        self.arka_plan(lambda: veri.sorgu(sql), self._bitti, self._hata)

    def _bitti(self, sonuc):
        kolonlar, satirlar = sonuc
        self.tablo.clear()
        self.tablo.setColumnCount(len(kolonlar))
        self.tablo.setHorizontalHeaderLabels(kolonlar)
        self.tablo.setRowCount(len(satirlar))
        for r, satir in enumerate(satirlar):
            for c, v in enumerate(satir):
                it = QTableWidgetItem("" if v is None else str(v))
                it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tablo.setItem(r, c, it)
        self.durum.setText(f"{self._ad}: {len(satirlar)} satır")

    def _hata(self, mesaj):
        self.durum.setText(f"Sorgu hatası: {mesaj}")


# ------------------------------------------------------------------- AYARLAR
class AyarSayfa(QWidget):
    kaydedildi = Signal()
    sunucu_sonucu = Signal(bool, str)

    def __init__(self, ayar_getir, arka_plan):
        super().__init__()
        self.ayar_getir = ayar_getir
        self.arka_plan = arka_plan

        dis = QVBoxLayout(self)
        dis.setContentsMargins(20, 10, 20, 20)
        kaydirma = QScrollArea()
        kaydirma.setWidgetResizable(True)
        ic = QWidget()
        lay = QVBoxLayout(ic)
        kaydirma.setWidget(ic)
        dis.addWidget(kaydirma, 1)

        # Görüntü
        g1 = QGroupBox("Görüntü kaynağı ve model")
        f1 = QFormLayout(g1)
        self.kaynak = QLineEdit()
        gozat = QPushButton("Gözat...")
        gozat.setObjectName("ikincil")
        gozat.clicked.connect(self._gozat)
        satir = QHBoxLayout()
        satir.addWidget(self.kaynak, 1)
        satir.addWidget(gozat)
        f1.addRow("Video / kamera:", satir)
        ipucu = QLabel("Video dosyası yolu, kamera için 0, IP kamera için rtsp://... adresi")
        ipucu.setStyleSheet("color:#bbb; font-size:12px;")
        f1.addRow("", ipucu)
        self.tekrar = QCheckBox("Video bitince başa sar")
        f1.addRow("", self.tekrar)
        self.model = QLineEdit()
        f1.addRow("YOLO modeli:", self.model)
        self.guven = QDoubleSpinBox()
        self.guven.setRange(0.05, 0.95)
        self.guven.setSingleStep(0.05)
        f1.addRow("Tespit güven eşiği:", self.guven)
        lay.addWidget(g1)

        # SQL
        g2 = QGroupBox("SQL Server")
        f2 = QFormLayout(g2)
        self.sunucu = QLineEdit()
        f2.addRow("Sunucu adı:", self.sunucu)
        self.veritabani = QLineEdit()
        f2.addRow("Veritabanı:", self.veritabani)
        self.driver = QComboBox()
        self.driver.setEditable(True)
        self.driver.addItems(db.yuklu_driverlar())
        f2.addRow("ODBC sürücüsü:", self.driver)
        self.winauth = QCheckBox("Windows kimlik doğrulaması")
        self.winauth.toggled.connect(self._auth_degisti)
        f2.addRow("", self.winauth)
        self.kullanici = QLineEdit()
        f2.addRow("Kullanıcı adı:", self.kullanici)
        self.sifre = QLineEdit()
        self.sifre.setEchoMode(QLineEdit.EchoMode.Password)
        f2.addRow("Şifre:", self.sifre)
        self.btn_test = QPushButton("🔌  Bağlantıyı Test Et")
        self.btn_test.setObjectName("ikincil")
        self.btn_test.clicked.connect(self.test_et)
        self.test_sonuc = QLabel("")
        self.test_sonuc.setWordWrap(True)
        f2.addRow(self.btn_test, self.test_sonuc)
        lay.addWidget(g2)

        # Sayım
        g3 = QGroupBox("Sayım ve durum kuralları")
        f3 = QFormLayout(g3)
        self.aralik = QSpinBox()
        self.aralik.setRange(1, 3600)
        self.aralik.setSuffix(" sn")
        f3.addRow("Veritabanına yazma aralığı:", self.aralik)
        self.dolu = QSpinBox()
        self.dolu.setRange(1, 3600)
        self.dolu.setSuffix(" sn")
        f3.addRow("Masa DOLU sayılması için süre:", self.dolu)
        self.bos = QSpinBox()
        self.bos.setRange(1, 3600)
        self.bos.setSuffix(" sn")
        f3.addRow("Masa BOŞ sayılması için süre:", self.bos)
        self.yogun = QSpinBox()
        self.yogun.setRange(1, 500)
        self.yogun.setSuffix(" kişi")
        f3.addRow("Büfe YOĞUN eşiği:", self.yogun)
        lay.addWidget(g3)
        lay.addStretch()

        alt = QHBoxLayout()
        self.btn_kaydet = QPushButton("💾  Kaydet")
        self.btn_kaydet.clicked.connect(self.kaydet)
        self.kayit_bilgi = QLabel("")
        self.kayit_bilgi.setObjectName("uyari")
        alt.addWidget(self.btn_kaydet)
        alt.addWidget(self.kayit_bilgi, 1)
        dis.addLayout(alt)

        self.forma_yukle(self.ayar_getir())

    def _auth_degisti(self, acik):
        self.kullanici.setEnabled(not acik)
        self.sifre.setEnabled(not acik)

    def _gozat(self):
        yol, _ = QFileDialog.getOpenFileName(
            self, "Video seç", str(config.BASE),
            "Video (*.mp4 *.avi *.mkv *.mov);;Tümü (*.*)")
        if yol:
            self.kaynak.setText(yol)

    def forma_yukle(self, a):
        self.kaynak.setText(str(a["kaynak"]))
        self.tekrar.setChecked(a["video_tekrar"])
        self.model.setText(a["model"])
        self.guven.setValue(a["guven"])
        self.sunucu.setText(a["sql_sunucu"])
        self.veritabani.setText(a["sql_veritabani"])
        if self.driver.findText(a["sql_driver"]) < 0:
            self.driver.addItem(a["sql_driver"])
        self.driver.setCurrentText(a["sql_driver"])
        self.winauth.setChecked(a["sql_windows_auth"])
        self._auth_degisti(a["sql_windows_auth"])
        self.kullanici.setText(a["sql_kullanici"])
        self.sifre.setText(a["sql_sifre"])
        self.aralik.setValue(a["yazma_araligi"])
        self.dolu.setValue(a["dolu_suresi"])
        self.bos.setValue(a["bos_suresi"])
        self.yogun.setValue(a["yogun_esigi"])

    def formdan_ayar(self):
        a = dict(self.ayar_getir())
        a.update({
            "kaynak": self.kaynak.text().strip(),
            "video_tekrar": self.tekrar.isChecked(),
            "model": self.model.text().strip(),
            "guven": round(self.guven.value(), 2),
            "sql_sunucu": self.sunucu.text().strip(),
            "sql_veritabani": self.veritabani.text().strip(),
            "sql_driver": self.driver.currentText().strip(),
            "sql_windows_auth": self.winauth.isChecked(),
            "sql_kullanici": self.kullanici.text(),
            "sql_sifre": self.sifre.text(),
            "yazma_araligi": self.aralik.value(),
            "dolu_suresi": self.dolu.value(),
            "bos_suresi": self.bos.value(),
            "yogun_esigi": self.yogun.value(),
        })
        return a

    def kaydet(self):
        config.ayarlari_kaydet(self.formdan_ayar())
        self.kayit_bilgi.setText("Kaydedildi. Çalışan sayım varsa durdurup yeniden başlat.")
        self.kaydedildi.emit()

    def test_et(self):
        self.btn_test.setEnabled(False)
        self.test_sonuc.setText("Bağlanılıyor...")
        veri = db.Veritabani(self.formdan_ayar())
        self.arka_plan(veri.test, self._test_ok, self._test_hata)

    def _test_ok(self, _):
        self.btn_test.setEnabled(True)
        self.test_sonuc.setText("✅ Bağlantı başarılı, tablolar hazır.")
        self.sunucu_sonucu.emit(True, "")

    def _test_hata(self, mesaj):
        self.btn_test.setEnabled(True)
        self.test_sonuc.setText(f"❌ {mesaj}")
        self.sunucu_sonucu.emit(False, mesaj)


# ------------------------------------------------------------- ANA PENCERE
class AnaPencere(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Restoran Takip")
        self.setMinimumSize(1100, 700)
        self.ayar = config.ayarlari_yukle()
        self.isci = None
        self._isler = []

        kok = QWidget()
        kok.setObjectName("kok")
        kok.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(kok)
        dikey = QVBoxLayout(kok)
        dikey.setContentsMargins(0, 0, 0, 0)
        dikey.setSpacing(0)

        # üst bar
        ust = QFrame()
        ust.setObjectName("ustbar")
        ul = QHBoxLayout(ust)
        ul.setContentsMargins(16, 10, 16, 10)
        self.btn_ana = QPushButton("🏠  Ana Sayfa")
        self.btn_ana.setObjectName("ikincil")
        self.btn_ana.clicked.connect(lambda: self.sayfa_ac(0))
        self.baslik = QLabel("Ana Sayfa")
        self.baslik.setObjectName("baslik")
        self.chip_sunucu = QLabel()
        self.chip_sunucu.setObjectName("chip")
        self.chip_sayim = QLabel()
        self.chip_sayim.setObjectName("chip")
        btn_cik = QPushButton("⏻  Çıkış")
        btn_cik.setObjectName("ikincil")
        btn_cik.clicked.connect(self.close)
        ul.addWidget(self.btn_ana)
        ul.addStretch()
        ul.addWidget(self.baslik)
        ul.addStretch()
        ul.addWidget(self.chip_sayim)
        ul.addSpacing(16)
        ul.addWidget(self.chip_sunucu)
        ul.addSpacing(16)
        ul.addWidget(btn_cik)
        dikey.addWidget(ust)

        # sayfalar
        self.yigin = QStackedWidget()
        dikey.addWidget(self.yigin, 1)
        self.ana = AnaSayfa()
        self.canli = CanliSayfa()
        self.bolge = BolgeSayfa(self.ayar_getir)
        self.rapor = RaporSayfa(self.ayar_getir, self.arka_plan)
        self.ayarlar = AyarSayfa(self.ayar_getir, self.arka_plan)
        for s in (self.ana, self.canli, self.bolge, self.rapor, self.ayarlar):
            self.yigin.addWidget(s)

        self.ana.git.connect(self.sayfa_ac)
        self.canli.baslat.connect(self.sayim_baslat)
        self.canli.durdur.connect(self.sayim_durdur)
        self.ayarlar.kaydedildi.connect(self.ayar_yenile)
        self.ayarlar.sunucu_sonucu.connect(self.sunucu_chip)

        self.sunucu_chip(None, "")
        self.sayim_chip(False)
        self.sayfa_ac(0)

        self.saat_zamanlayici = QTimer(self)
        self.saat_zamanlayici.timeout.connect(self.ana.saati_guncelle)
        self.saat_zamanlayici.start(1000)
        QTimer.singleShot(500, self.ilk_test)

    # --- yardımcılar ---
    def ayar_getir(self):
        return self.ayar

    def ayar_yenile(self):
        self.ayar = config.ayarlari_yukle()

    def arka_plan(self, fn, bitti=None, hata=None):
        self._isler = [t for t in self._isler if t.isRunning()]
        t = Is(fn)
        if bitti:
            t.bitti.connect(bitti)
        if hata:
            t.hata.connect(hata)
        self._isler.append(t)
        t.start()

    def sayfa_ac(self, i):
        self.yigin.setCurrentIndex(i)
        self.baslik.setText(BASLIKLAR[i])
        self.btn_ana.setVisible(i != 0)
        if i == 2:
            self.bolge.hazirla()

    def sunucu_chip(self, ok, mesaj):
        if ok is None:
            renk, metin = "#aaaaaa", "Sunucu: kontrol ediliyor"
        elif ok:
            renk, metin = "#2ecc71", "Sunucu: Bağlı"
        else:
            renk, metin = "#e74c3c", "Sunucu: Bağlı değil"
        self.chip_sunucu.setText(f"<span style='color:{renk}'>●</span> {metin}")
        self.chip_sunucu.setToolTip(mesaj)

    def sayim_chip(self, calisiyor):
        renk = "#2ecc71" if calisiyor else "#aaaaaa"
        metin = "Sayım: çalışıyor" if calisiyor else "Sayım: durdu"
        self.chip_sayim.setText(f"<span style='color:{renk}'>●</span> {metin}")

    def ilk_test(self):
        veri = db.Veritabani(self.ayar)
        self.arka_plan(veri.test, self._ilk_test_ok, self._ilk_test_hata)

    def _ilk_test_ok(self, _):
        self.sunucu_chip(True, "")

    def _ilk_test_hata(self, mesaj):
        self.sunucu_chip(False, mesaj)

    # --- sayım ---
    def sayim_baslat(self):
        if self.isci is not None and self.isci.isRunning():
            return
        self.canli.mesaj.setText("Model yükleniyor...")
        self.isci = SayimIsci(dict(self.ayar))
        self.isci.kare.connect(self.canli.kare_goster)
        self.isci.durum.connect(self.canli.durum_guncelle)
        self.isci.db_durum.connect(self.sayim_db_durum)
        self.isci.hata.connect(self.sayim_hata)
        self.isci.bilgi.connect(self.canli.mesaj.setText)
        self.isci.finished.connect(self.sayim_bitti)
        self.isci.start()
        self.canli.calisiyor(True)
        self.sayim_chip(True)

    def sayim_durdur(self):
        if self.isci is not None:
            self.isci.durdur()
            self.canli.btn_durdur.setEnabled(False)

    def sayim_bitti(self):
        self.canli.calisiyor(False)
        self.sayim_chip(False)

    def sayim_db_durum(self, ok, mesaj):
        self.sunucu_chip(ok, mesaj)
        if ok:
            self.canli.mesaj.setText("")
        else:
            self.canli.mesaj.setText("Veritabanına yazılamıyor, sayım devam ediyor. "
                                     "Bağlantı 15 sn'de bir yeniden denenir.")

    def sayim_hata(self, mesaj):
        self.canli.mesaj.setText(mesaj)
        QMessageBox.warning(self, "Sayım durdu", mesaj)

    def closeEvent(self, e):
        if self.isci is not None and self.isci.isRunning():
            self.isci.durdur()
            self.isci.wait(8000)
        e.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STIL)
    pencere = AnaPencere()
    pencere.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
