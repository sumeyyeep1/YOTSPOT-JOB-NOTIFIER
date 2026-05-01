# Standart ve sağlam bir Python Debian imajı kullanıyoruz
FROM python:3.11-bookworm

WORKDIR /app

# Sadece requirements.txt'yi kopyala ve Python paketlerini kur
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# KRİTİK NOKTA: Playwright tarayıcısını ve TÜM Linux bağımlılıklarını 
# program çalışırken değil, sistem inşa edilirken (root yetkisiyle) kuruyoruz.
RUN playwright install --with-deps chromium

# Kodların geri kalanını kopyala
COPY . .

# Botu çalıştır
CMD ["python", "is_ilani_takip.py"]