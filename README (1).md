# Yotspot Job Notifier

Yotspot iş arama sayfasını belirli aralıklarla kontrol eder, kriterlere uyan yeni ilanları daha önce gördükleriyle karşılaştırır ve yeni ilan varsa bildirim gönderir.

## Bildirim sistemi nasıl çalışır?

Program sürekli açık kaldığı sürece `config.json` içindeki `kontrol_araligi` kadar bekler, sonra `site_url` adresini yeniden kontrol eder.

Akış:

1. Yotspot iş ilanları çekilir.
2. Pozisyon, lokasyon, ilan numarası, detaylar ve link ayrıştırılır.
3. `arama_kriterleri` ile filtrelenir.
4. Daha önce bildirilen ilanlar `gorulmus_ilanlar.json` dosyasındaki kayıtla karşılaştırılır.
5. Yeni ilan varsa Gmail üzerinden email bildirimi gönderilir.

Program kapalıysa kontrol yapılmaz. Sürekli çalışması için bilgisayarda açık bırakabilir, Windows başlangıcına ekleyebilir veya daha sağlıklı olarak küçük bir VPS/sunucuda çalıştırabilirsin.

## Bildirim kanalı

Bu sürüm sadece email gönderir. SMTP kullanıcı adı, uygulama şifresi ve alıcı adresi `config.json` içinde tutulmaz; gizli bilgiler `.env` dosyasından okunur.

## Arkadaşından alman gereken bilgiler

İş kriterleri:

- Aradığı pozisyonlar: `deckhand`, `junior deckhand`
- İstediği lokasyonlar: örn. `United States`, `France`, `Spain`; fark etmezse boş bırakılır
- İlan tipi tercihleri: permanent, seasonal, daywork, rotational vb.
- Maaş/para birimi alt sınırı isteniyor mu?
- Yat tipi veya boyu önemli mi?
- Kaç dakikada bir kontrol edilsin? Öneri: 10-30 dakika

Bildirim bilgileri:

- Alıcı email adresi
- Gönderen Gmail adresi
- Gönderen Gmail için uygulama şifresi
- Bildirimin kime gideceği: sana mı, arkadaşına mı?

Operasyon:

- Program nerede çalışacak? Arkadaşının bilgisayarı, senin bilgisayarın veya VPS
- Bilgisayar kapanınca bildirimlerin duracağı kabul ediliyor mu?
- Yotspot hesabıyla giriş gerektiren kapalı ilanlar takip edilecek mi? Giriş gerekiyorsa ayrıca oturum/cookie tabanlı geliştirme gerekir.

## Kurulum

Python 3.10+ kurulu olmalı.

```bash
pip install -r requirements.txt
```

Çalıştırma:

```bash
python is_ilani_takip.py
```

## Yapılandırma

`config.json` örneği:

```json
{
  "site_url": "https://www.yotspot.com/job-search.html",
  "kontrol_araligi": 600,
  "http_timeout": 45,
  "istek_tekrar_sayisi": 3,
  "istek_tekrar_bekleme": 15,
  "maksimum_ilan": 20,
  "maksimum_sayfa": 1,
  "email": {
    "aktif": true
  },
  "arama_kriterleri": {
    "pozisyonlar": ["Deckhand", "Junior Deckhand"],
    "tam_pozisyon_eslesmesi": true,
    "anahtar_kelimeler": ["deckhand"],
    "konumlar": [],
    "sehir": ""
  }
}
```

Lokasyon filtrelemek için:

```json
"konumlar": ["United States", "France"]
```

Tüm lokasyonları almak için `konumlar` boş kalmalı.

`http_timeout`, Yotspot'un cevap vermesi için beklenecek saniyedir. `istek_tekrar_sayisi` ve `istek_tekrar_bekleme`, geçici bağlantı hatalarında aynı kontrol içinde tekrar deneme yapmak için kullanılır.

Yotspot filtreleri ayrı bir HTML sayfası açmadığı için `site_url` genel iş sayfasıdır. Program varsayılan olarak ilk sayfadaki en güncel ilanları kontrol eder. `maksimum_sayfa` değerini artırırsan eski sayfalara da bakar, ama günlük bildirim için genelde ilk sayfa yeterlidir.

## Email ayarı

`.env` dosyası:

```env
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_SENDER=your-email@gmail.com
EMAIL_PASSWORD=your-gmail-app-password
EMAIL_RECIPIENT=recipient@example.com
```

Gmail kullanıyorsan normal hesap şifresini değil, Google hesabından oluşturulan uygulama şifresini kullanmalısın.

## Notlar

- Yotspot sayfa yapısını değiştirirse parser tekrar güncellenebilir.
- Siteyi çok sık sorgulama; 10 dakika makul bir başlangıçtır.
- Gerçek email şifresini public GitHub deposuna koyma. `.env` dosyası `.gitignore` içindedir.
