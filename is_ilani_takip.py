#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
İş İlanı Takip ve Bildirim Sistemi
Web scraping ile iş ilanlarını takip eder ve yeni ilanlar için bildirim gönderir.
"""

import os
import sys
import time
import json
import socket
import smtplib
import threading
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from http.server import HTTPServer, BaseHTTPRequestHandler

# Senin daha önce kullandığın diğer kütüphaneler (Playwright, bs4 vb. varsa buraya ekli kalsın)
import requests
from bs4 import BeautifulSoup
import hashlib
import re
import subprocess
from pathlib import Path
from urllib.parse import urljoin


# =====================================================================
# 1. IPv6 HATASINI ÇÖZEN SİHİRLİ YAMA (Network is unreachable çözümü)
# =====================================================================
eski_getaddrinfo = socket.getaddrinfo

def sadece_ipv4_getaddrinfo(*args, **kwargs):
    cevaplar = eski_getaddrinfo(*args, **kwargs)
    # Sadece IPv4 (AF_INET) olan bağlantılara izin ver
    return [cevap for cevap in cevaplar if cevap[0] == socket.AF_INET]

socket.getaddrinfo = sadece_ipv4_getaddrinfo


# =====================================================================
# 2. RENDER.COM SAHTE WEB SUNUCUSU (No open ports hatası çözümü)
# =====================================================================
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Yotspot Botu Sorunsuz Calisiyor!")
        
    # Terminalde log kirliliği yapmaması için HTTP loglarını kapatıyoruz
    def log_message(self, format, *args):
        pass

def run_dummy_server():
    # Render'ın bize atadığı portu alıyoruz, bulamazsa 10000 kullanıyor
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    print(f"[*] Render sahte web sunucusu {port} portunda baslatildi.")
    server.serve_forever()


# =====================================================================
# 3. ASIL İŞ İLANI TAKİP BOTU SINIFI
# =====================================================================
class IsIlaniTakip:
    def __init__(self, config_file="config.json"):
        # Kendi config yükleme ayarların
        self.config_file = config_file
        # ... kendi init kodlarının geri kalanı ...

    def email_gonder(self, yeni_ilanlar):
        """Yeni ilanları e-posta ile gönderir."""
        # Şifreleri Render'ın Environment Variables kısmından çekiyoruz
        gonderici_email = os.environ.get("EMAIL_SENDER")
        gonderici_sifre = os.environ.get("EMAIL_PASSWORD")
        alici_email = os.environ.get("EMAIL_RECIPIENT")

        if not all([gonderici_email, gonderici_sifre, alici_email]):
            print("[HATA] E-posta ayarları (Environment Variables) eksik!")
            return

        msg = MIMEMultipart()
        msg['From'] = gonderici_email
        msg['To'] = alici_email
        msg['Subject'] = f"Yotspot: {len(yeni_ilanlar)} Yeni İlan Bulundu!"

        # E-posta içeriğini oluştur
        govde = "Yeni ilanlar bulundu:\n\n"
        for ilan in yeni_ilanlar:
            govde += f"- {ilan}\n"
        
        msg.attach(MIMEText(govde, 'plain', 'utf-8'))

        try:
            # 465 SSL Portu ile sorunsuz gönderim yapıyoruz
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(gonderici_email, gonderici_sifre)
                server.send_message(msg)
            print("✅ E-posta başarıyla gönderildi!")
        except Exception as e:
            print(f"❌ E-posta gönderme hatası: {e}")

    def ilanlari_cek(self):
        """Playwright ile Yotspot'a girip ilanları çeken fonksiyon"""
        # =========================================================
        # KENDİ PLAYWRIGHT TARAMA KODLARINI BURAYA YAPIŞTIR
        # =========================================================
        pass

    def calistir(self):
        print("🚀 İş İlanı Takip Sistemi Başlatıldı")
        # Kendi döngün (örneğin while True: ilanlari_cek() ... time.sleep(600))
        # =========================================================
        # KENDİ DÖNGÜ KODLARINI BURAYA YAPIŞTIR
        # =========================================================
        pass

    def test_et(self):
        print("Test modu çalışıyor...")
        pass


# =====================================================================
# 4. SİSTEMİN BAŞLATILMA NOKTASI
# =====================================================================
if __name__ == "__main__":
    # Render fişi çekmesin diye sahte sunucuyu arka planda (Thread) çalıştırıyoruz
    threading.Thread(target=run_dummy_server, daemon=True).start()

    # Asıl botumuzu başlatıyoruz
    takip = IsIlaniTakip()
    
    if "--test" in sys.argv:
        takip.test_et()
    else:
        takip.calistir()