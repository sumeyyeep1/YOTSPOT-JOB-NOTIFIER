# Microsoft'un resmi, içinde Playwright'ın tüm kütüphaneleri hazır olan imajı
FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Çalışma klasörünü oluştur
WORKDIR /app

# Sadece requirements.txt'yi kopyala ve Python paketlerini kur
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Projenin geri kalan tüm dosyalarını kopyala
COPY . .

# Botu çalıştır
CMD ["python", "is_ilani_takip.py"]