"""SQL Server işlemleri (pyodbc)."""
from datetime import datetime


def baglanti_dizesi(a):
    parca = [
        f"DRIVER={{{a['sql_driver']}}}",
        f"SERVER={a['sql_sunucu']}",
        f"DATABASE={a['sql_veritabani']}",
    ]
    if a["sql_windows_auth"]:
        parca.append("Trusted_Connection=yes")
    else:
        parca.append(f"UID={a['sql_kullanici']}")
        parca.append(f"PWD={a['sql_sifre']}")
    if "18" in a["sql_driver"]:
        parca.append("TrustServerCertificate=yes")
    return ";".join(parca) + ";"


def yuklu_driverlar():
    try:
        import pyodbc
        return [d for d in pyodbc.drivers() if "SQL Server" in d]
    except Exception:
        return []


SEMA = [
    """IF OBJECT_ID(N'dbo.BolgeSayim', N'U') IS NULL
       CREATE TABLE dbo.BolgeSayim (
           Id INT IDENTITY(1,1) PRIMARY KEY,
           Zaman DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
           BolgeAdi NVARCHAR(50) NOT NULL,
           KisiSayisi INT NOT NULL)""",
    """IF OBJECT_ID(N'dbo.MasaDurum', N'U') IS NULL
       CREATE TABLE dbo.MasaDurum (
           Id INT IDENTITY(1,1) PRIMARY KEY,
           Zaman DATETIME2 NOT NULL DEFAULT SYSDATETIME(),
           MasaAdi NVARCHAR(50) NOT NULL,
           Durum NVARCHAR(10) NOT NULL)""",
]


class Veritabani:
    def __init__(self, ayar):
        self.ayar = ayar
        self.baglanti = None

    def baglan(self):
        try:
            import pyodbc
        except ImportError:
            raise RuntimeError("pyodbc kurulu değil (pip install pyodbc)")
        self.baglanti = pyodbc.connect(baglanti_dizesi(self.ayar), timeout=5)

    def kapat(self):
        if self.baglanti is not None:
            try:
                self.baglanti.close()
            except Exception:
                pass
            self.baglanti = None

    def sema_olustur(self):
        cur = self.baglanti.cursor()
        for sql in SEMA:
            cur.execute(sql)
        self.baglanti.commit()

    def sayim_yaz(self, satirlar):
        """satirlar: [(bolge_adi, kisi_sayisi), ...]"""
        cur = self.baglanti.cursor()
        cur.executemany(
            "INSERT INTO dbo.BolgeSayim (BolgeAdi, KisiSayisi) VALUES (?, ?)",
            [(ad, int(n)) for ad, n in satirlar],
        )
        self.baglanti.commit()

    def durum_yaz(self, satirlar):
        """satirlar: [(datetime, masa_adi, 'Dolu'|'Bos'), ...]"""
        cur = self.baglanti.cursor()
        cur.executemany(
            "INSERT INTO dbo.MasaDurum (Zaman, MasaAdi, Durum) VALUES (?, ?, ?)",
            satirlar,
        )
        self.baglanti.commit()

    def sorgu(self, sql):
        """(kolon_adlari, satirlar) döndürür; bağlantıyı kendisi açıp kapatır."""
        self.baglan()
        try:
            cur = self.baglanti.cursor()
            cur.execute(sql)
            kolonlar = [c[0] for c in cur.description]
            satirlar = [list(r) for r in cur.fetchall()]
            return kolonlar, satirlar
        finally:
            self.kapat()

    def test(self):
        """Bağlanır, tabloları (yoksa) oluşturur, kapatır."""
        self.baglan()
        try:
            self.sema_olustur()
        finally:
            self.kapat()
        return True


RAPORLAR = {
    "Anlık masa durumu": """
        SELECT MasaAdi, Durum, Zaman AS SonDegisim FROM (
            SELECT MasaAdi, Durum, Zaman,
                   ROW_NUMBER() OVER (PARTITION BY MasaAdi ORDER BY Id DESC) AS rn
            FROM dbo.MasaDurum) t
        WHERE rn = 1 ORDER BY LEN(MasaAdi), MasaAdi""",
    "Masa / alan özeti": """
        SELECT BolgeAdi, COUNT(*) AS Kayit,
               CAST(AVG(KisiSayisi * 1.0) AS DECIMAL(6,2)) AS OrtalamaKisi,
               MAX(KisiSayisi) AS EnFazla,
               CAST(100.0 * SUM(CASE WHEN KisiSayisi > 0 THEN 1 ELSE 0 END)
                    / COUNT(*) AS DECIMAL(5,1)) AS DoluYuzde
        FROM dbo.BolgeSayim GROUP BY BolgeAdi ORDER BY LEN(BolgeAdi), BolgeAdi""",
    "Saat bazlı yoğunluk": """
        SELECT DATEPART(HOUR, Zaman) AS Saat,
               CAST(AVG(KisiSayisi * 1.0) AS DECIMAL(6,2)) AS OrtalamaKisi,
               MAX(KisiSayisi) AS EnFazla
        FROM dbo.BolgeSayim WHERE BolgeAdi NOT LIKE 'masa%'
        GROUP BY DATEPART(HOUR, Zaman) ORDER BY Saat""",
    "Son durum değişiklikleri": """
        SELECT TOP 100 Zaman, MasaAdi, Durum FROM dbo.MasaDurum ORDER BY Id DESC""",
}
