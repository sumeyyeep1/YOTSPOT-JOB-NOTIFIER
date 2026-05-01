#!/usr/bin/env python3
"""
İş İlanı Takip ve Bildirim Sistemi
Web scraping ile iş ilanlarını takip eder ve yeni ilanlar için bildirim gönderir.
"""

import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import os
import re
from urllib.parse import urljoin

class IsIlaniTakip:
    def __init__(self, config_file="config.json"):
        """
        Yapılandırma dosyasından ayarları yükle
        """
        self.env = self.load_env()
        self.config = self.load_config(config_file)
        self.gorulmus_ilanlar_file = "gorulmus_ilanlar.json"
        self.gorulmus_ilanlar = self.load_gorulmus_ilanlar()

    def load_env(self, env_file=".env"):
        """Basit .env dosyasını yükle ve ortam değişkenleriyle birleştir."""
        env = {}

        if os.path.exists(env_file):
            with open(env_file, 'r', encoding='utf-8-sig') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or '=' not in line:
                        continue

                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip().strip('"').strip("'")

        env.update(os.environ)
        return env
    
    def load_config(self, config_file):
        """Yapılandırma dosyasını yükle"""
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Varsayılan yapılandırma
            default_config = {
                "site_url": "https://www.yotspot.com/job-search.html",
                "kontrol_araligi": 600,  # 10 dakika
                "http_timeout": 45,
                "istek_tekrar_sayisi": 3,
                "istek_tekrar_bekleme": 15,
                "maksimum_ilan": 20,
                "maksimum_sayfa": 1,
                "email": {
                    "aktif": True
                },
                "arama_kriterleri": {
                    "pozisyonlar": ["Deckhand", "Junior Deckhand"],
                    "tam_pozisyon_eslesmesi": True,
                    "anahtar_kelimeler": ["deckhand"],
                    "konumlar": [],
                    "sehir": ""
                }
            }
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
            return default_config
    
    def load_gorulmus_ilanlar(self):
        """Önceden görülmüş ilanları yükle"""
        if os.path.exists(self.gorulmus_ilanlar_file):
            with open(self.gorulmus_ilanlar_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []

    def http_session_olustur(self):
        """Yotspot gibi bot koruması olan sayfalar için uygun HTTP oturumu oluştur."""
        try:
            import cloudscraper
            return cloudscraper.create_scraper()
        except ImportError:
            return requests.Session()
    
    def save_gorulmus_ilanlar(self):
        """Görülmüş ilanları kaydet"""
        with open(self.gorulmus_ilanlar_file, 'w', encoding='utf-8') as f:
            json.dump(self.gorulmus_ilanlar, f, indent=4, ensure_ascii=False)
    
    def ilan_hash_olustur(self, ilan_baslik, sirket, link=""):
        """İlan için benzersiz hash oluştur"""
        ilan_str = f"{ilan_baslik}_{sirket}_{link}"
        return hashlib.md5(ilan_str.encode()).hexdigest()
    
    def ilanlari_cek(self):
        """
        Yotspot iş ilanı sayfasından ilanları çek.
        """
        try:
            headers = {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/124.0 Safari/537.36'
                ),
                'Accept-Language': 'en-US,en;q=0.9,tr;q=0.8'
            }
            
            session = self.http_session_olustur()
            return self.yotspot_sayfalari_cek(session, headers)
            
        except requests.RequestException as e:
            print(f"İstek hatası: {e}")
            return None
        except Exception as e:
            print(f"Genel hata: {e}")
            return None

    def yotspot_sayfalari_cek(self, session, headers):
        """Deckhand sonuçlarındaki sayfaları gezerek ilanları çek."""
        ilanlar = []
        gorulen_linkler = set()
        gorulen_sayfalar = set()
        url = self.config['site_url']
        maksimum_ilan = self.config.get('maksimum_ilan', 300)
        maksimum_sayfa = self.config.get('maksimum_sayfa', 30)

        for sayfa_no in range(1, maksimum_sayfa + 1):
            if not url or url in gorulen_sayfalar:
                break

            gorulen_sayfalar.add(url)
            soup = self.yotspot_sayfa_cek(session, headers, url, sayfa_no)
            if soup is None:
                return None if not ilanlar else ilanlar

            sayfa_ilanlari = self.yotspot_ilanlarini_parse_et(soup)
            yeni_sayfa_ilanlari = 0

            for ilan in sayfa_ilanlari:
                if ilan['link'] in gorulen_linkler:
                    continue

                gorulen_linkler.add(ilan['link'])
                ilanlar.append(ilan)
                yeni_sayfa_ilanlari += 1

                if len(ilanlar) >= maksimum_ilan:
                    return ilanlar

                    print(f"  Sayfa {sayfa_no}: {yeni_sayfa_ilanlari} aday ilan kontrol edildi")

            url = self.sonraki_sayfa_linki_bul(soup, url)

        return ilanlar

    def yotspot_sayfa_cek(self, session, headers, url, sayfa_no):
        """Tek bir Yotspot sonuç sayfasını retry ile çek."""
        son_hata = None
        tekrar_sayisi = self.config.get('istek_tekrar_sayisi', 3)
        tekrar_bekleme = self.config.get('istek_tekrar_bekleme', 15)
        timeout = self.config.get('http_timeout', 45)

        for deneme in range(1, tekrar_sayisi + 1):
            try:
                response = session.get(url, headers=headers, timeout=timeout)
                response.raise_for_status()
                return BeautifulSoup(response.content, 'html.parser')
            except requests.RequestException as e:
                son_hata = e
                print(f"Sayfa {sayfa_no} istek denemesi başarısız ({deneme}/{tekrar_sayisi}): {e}")

                if deneme < tekrar_sayisi:
                    time.sleep(tekrar_bekleme)

        print(f"İstek hatası: {son_hata}")
        return None

    def sonraki_sayfa_linki_bul(self, soup, mevcut_url):
        """Yotspot sayfalamasındaki Next linkini bul."""
        next_link = soup.find('a', string=re.compile(r'^\s*Next\s*$', re.I))
        if not next_link:
            next_link = soup.find('a', attrs={'rel': re.compile(r'next', re.I)})

        if not next_link or not next_link.get('href'):
            return None

        return urljoin(mevcut_url, next_link['href'])

    def yotspot_ilanlarini_parse_et(self, soup):
        """Yotspot listesindeki ilan kartlarını esnek şekilde ayrıştır."""
        ilanlar = []
        gorulen_linkler = set()
        maksimum_ilan = self.config.get('maksimum_ilan', 30)

        for gereksiz in soup(['script', 'style', 'noscript']):
            gereksiz.decompose()

        for link_elemani in soup.find_all('a', href=True):
            link_metni = link_elemani.get_text(" ", strip=True).lower()
            href = link_elemani.get('href', '')

            if 'view job' not in link_metni and not re.search(r'job|vacanc|position', href, re.I):
                continue

            kart = self.yotspot_ilan_karti_bul(link_elemani)
            if not kart:
                continue

            ilan = self.yotspot_ilan_kartini_parse_et(kart, href)
            if not ilan or ilan['link'] in gorulen_linkler:
                continue

            gorulen_linkler.add(ilan['link'])

            if self.ilan_kriterlere_uyuyor(ilan):
                ilanlar.append(ilan)

            if len(ilanlar) >= maksimum_ilan:
                break

        return ilanlar

    def yotspot_ilan_karti_bul(self, link_elemani):
        """View Job linkinin etrafındaki anlamlı ilan bloğunu bul."""
        for parent in link_elemani.parents:
            if not getattr(parent, 'get_text', None) or parent.name == 'body':
                break

            metin = parent.get_text(" ", strip=True)
            if 40 <= len(metin) <= 1800 and re.search(r'Posted|Starting|Permanent|Seasonal|Daywork', metin, re.I):
                return parent

        return None

    def yotspot_ilan_kartini_parse_et(self, kart, href):
        """Tek bir Yotspot ilan kartından alanları çıkar."""
        satirlar = [
            satir.strip()
            for satir in kart.stripped_strings
            if satir.strip()
        ]
        satirlar = [satir for satir in satirlar if satir.lower() not in {'view job', 'apply', 'save'}]

        if not satirlar:
            return None

        baslik = self.yotspot_baslik_bul(satirlar)
        if not baslik:
            return None

        link = urljoin(self.config['site_url'], href)
        ilan_no = self.ilan_numarasi_bul(" ".join(satirlar + [href]))
        detaylar = [
            satir for satir in satirlar
            if self.yotspot_baslik_temizle(satir) != baslik
        ][:8]
        konum = self.yotspot_konum_bul(detaylar)
        yayin_tarihi = next((satir for satir in detaylar if satir.lower().startswith('posted')), '')

        return {
            'baslik': baslik,
            'sirket': 'Yotspot',
            'link': link,
            'ilan_no': ilan_no,
            'konum': konum,
            'detaylar': detaylar,
            'yayin_tarihi': yayin_tarihi,
            'tarih': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def yotspot_baslik_bul(self, satirlar):
        """Yotspot kartındaki pozisyon başlığını bul ve etiketleri temizle."""
        for satir in satirlar:
            if re.search(r'#\d+', satir):
                return self.yotspot_baslik_temizle(satir)

        engellenenler = ('starting ', 'posted ', 'permanent', 'seasonal', 'daywork')
        for satir in satirlar:
            if not satir.lower().startswith(engellenenler):
                return self.yotspot_baslik_temizle(satir)

        return ''

    def yotspot_baslik_temizle(self, metin):
        """Yotspot başlığındaki rozet metinlerini temizle."""
        return re.sub(r'^(Featured|New|Updated)\s+', '', metin, flags=re.I).strip()

    def ilan_numarasi_bul(self, metin):
        """Yotspot ilan numarasını bul."""
        eslesme = re.search(r'#(\d+)', metin)
        return eslesme.group(1) if eslesme else ''

    def yotspot_konum_bul(self, detaylar):
        """Detay satırlarından lokasyon gibi görünen ilk değeri bul."""
        engellenen = (
            'starting ', 'posted ', 'permanent', 'seasonal', 'rotational',
            'temporary', 'daywork', 'private', 'charter'
        )
        para_birimleri = ('usd', 'eur', 'gbp', '$', '€', '£')

        for detay in detaylar:
            detay_lower = detay.lower()
            if detay_lower.startswith(engellenen):
                continue
            if any(para in detay_lower for para in para_birimleri):
                continue
            if 'yacht' in detay_lower or 'vessel' in detay_lower or 'shore based' in detay_lower:
                continue
            return detay

        return ''
    
    def anahtar_kelime_kontrol(self, metin):
        """İlana anahtar kelime kontrolü yap"""
        metin_lower = metin.lower()
        anahtar_kelimeler = self.config.get('arama_kriterleri', {}).get('anahtar_kelimeler', [])
        if not anahtar_kelimeler:
            return True
        
        # En az bir anahtar kelime var mı kontrol et
        for kelime in anahtar_kelimeler:
            if kelime.lower() in metin_lower:
                return True
        return False

    def ilan_kriterlere_uyuyor(self, ilan):
        """İlanı anahtar kelime ve lokasyon kriterlerine göre filtrele."""
        kriterler = self.config.get('arama_kriterleri', {})

        if kriterler.get('tam_pozisyon_eslesmesi', False):
            pozisyonlar = kriterler.get('pozisyonlar') or []
            eski_pozisyon = kriterler.get('pozisyon')
            if eski_pozisyon:
                pozisyonlar.append(eski_pozisyon)

            beklenen_pozisyonlar = {
                pozisyon.strip().lower()
                for pozisyon in pozisyonlar
                if pozisyon.strip()
            }
            ilan_pozisyonu = self.pozisyon_adi_temizle(ilan.get('baslik', '')).lower()

            if beklenen_pozisyonlar and ilan_pozisyonu not in beklenen_pozisyonlar:
                return False

        aranacak_metin = " ".join([
            ilan.get('baslik', ''),
            ilan.get('konum', ''),
            " ".join(ilan.get('detaylar', []))
        ])

        if not self.anahtar_kelime_kontrol(aranacak_metin):
            return False

        konumlar = kriterler.get('konumlar') or []
        eski_sehir = kriterler.get('sehir')
        if eski_sehir:
            konumlar.append(eski_sehir)

        if not konumlar:
            return True

        aranacak_metin_lower = aranacak_metin.lower()
        return any(konum.lower() in aranacak_metin_lower for konum in konumlar)

    def pozisyon_adi_temizle(self, baslik):
        """Başlıktan ilan numarası ve rozetleri çıkarıp pozisyon adını döndür."""
        pozisyon = self.yotspot_baslik_temizle(baslik)
        pozisyon = re.sub(r'\s*#\d+.*$', '', pozisyon).strip()
        pozisyon = re.sub(r'\s+Team/Couple$', '', pozisyon, flags=re.I).strip()
        return pozisyon
    
    def yeni_ilan_mi(self, ilan):
        """İlan daha önce görüldü mü kontrol et"""
        ilan_hash = self.ilan_hash_olustur(ilan['baslik'], ilan['sirket'], ilan.get('link', ''))
        return ilan_hash not in self.gorulmus_ilanlar
    
    def email_gonder(self, ilanlar):
        """Email ile bildirim gönder"""
        if not self.config.get('email', {}).get('aktif', False):
            return

        smtp_server = self.env.get('EMAIL_SMTP_SERVER', 'smtp.gmail.com')
        smtp_port = int(self.env.get('EMAIL_SMTP_PORT', '587'))
        gonderici_email = self.env.get('EMAIL_SENDER', '')
        gonderici_sifre = self.env.get('EMAIL_PASSWORD', '')
        alici_email = self.env.get('EMAIL_RECIPIENT', '')

        if not all([smtp_server, smtp_port, gonderici_email, gonderici_sifre, alici_email]):
            print("Email ayarları eksik: .env dosyasındaki EMAIL_* değerlerini kontrol edin")
            return
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"🔔 {len(ilanlar)} Yeni İş İlanı Bulundu!"
            msg['From'] = gonderici_email
            msg['To'] = alici_email
            
            # HTML içerik oluştur
            html = "<html><body><h2>Yeni İş İlanları</h2><ul>"
            for ilan in ilanlar:
                detay_html = "".join(f"<li>{detay}</li>" for detay in ilan.get('detaylar', []))
                html += f"""
                <li>
                    <strong>{ilan['baslik']}</strong><br>
                    Kaynak: {ilan['sirket']}<br>
                    Konum: {ilan.get('konum', '-') or '-'}<br>
                    İlan No: {ilan.get('ilan_no', '-') or '-'}<br>
                    <ul>{detay_html}</ul>
                    <a href="{ilan['link']}">İlanı Görüntüle</a><br>
                    Kontrol Tarihi: {ilan['tarih']}
                </li><br>
                """
            html += "</ul></body></html>"
            
            part = MIMEText(html, 'html')
            msg.attach(part)
            
            # SMTP ile gönder
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(gonderici_email, gonderici_sifre)
                server.send_message(msg)
            
            print(f"✉️  Email gönderildi: {len(ilanlar)} ilan")
            
        except Exception as e:
            print(f"Email gönderme hatası: {e}")

    def calistir(self):
        """Ana döngü - sürekli kontrol et"""
        print("🚀 İş İlanı Takip Sistemi Başlatıldı")
        print(f"📍 Site: {self.config['site_url']}")
        print(f"⏱️  Kontrol Aralığı: {self.config['kontrol_araligi']} saniye")
        print(f"🔍 Anahtar Kelimeler: {self.config['arama_kriterleri']['anahtar_kelimeler']}")
        print("-" * 50)
        
        while True:
            try:
                print(f"\n⏰ Kontrol ediliyor... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                
                # İlanları çek
                ilanlar = self.ilanlari_cek()
                
                if ilanlar is None:
                    print("❌ Yotspot bağlantısı kurulamadı; sonraki kontrolde tekrar denenecek")
                elif not ilanlar:
                    print("ℹ️  Deckhand kriterine uyan ilan bulunamadı")
                else:
                    print(f"📋 Bu kontrolde {len(ilanlar)} aday ilan bulundu")
                    
                    # Yeni ilanları filtrele
                    yeni_ilanlar = [ilan for ilan in ilanlar if self.yeni_ilan_mi(ilan)]
                    eski_ilan_sayisi = len(ilanlar) - len(yeni_ilanlar)
                    
                    if yeni_ilanlar:
                        print(f"🆕 {len(yeni_ilanlar)} YENİ İLAN BULUNDU!")
                        if eski_ilan_sayisi:
                            print(f"ℹ️  {eski_ilan_sayisi} ilan daha önce bildirildiği için atlandı")
                        
                        # Bildirimleri gönder
                        self.email_gonder(yeni_ilanlar)
                        
                        # Görülmüş olarak işaretle
                        for ilan in yeni_ilanlar:
                            ilan_hash = self.ilan_hash_olustur(ilan['baslik'], ilan['sirket'], ilan.get('link', ''))
                            self.gorulmus_ilanlar.append(ilan_hash)
                            print(f"  ✓ {ilan['baslik']} - {ilan.get('konum', ilan['sirket'])}")
                        
                        self.save_gorulmus_ilanlar()
                    else:
                        print(f"ℹ️  Yeni ilan yok; {eski_ilan_sayisi} ilan daha önce görülmüş")
                
                # Bekleme
                print(f"⏳ Sonraki kontrol {self.config['kontrol_araligi']} saniye sonra...")
                time.sleep(self.config['kontrol_araligi'])
                
            except KeyboardInterrupt:
                print("\n\n👋 Program sonlandırıldı")
                break
            except Exception as e:
                print(f"❌ Hata oluştu: {e}")
                time.sleep(60)  # Hata durumunda 1 dakika bekle


if __name__ == "__main__":
    takip = IsIlaniTakip()
    takip.calistir()
