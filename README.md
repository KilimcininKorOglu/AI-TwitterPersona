# 🤖 AI-TwitterPersona

Türkiye'nin gerçek zamanlı trend konularını takip eden ve Google Gemini AI ile kişisel tarzda tweetler üreten otomatik Twitter botu.

## 🚀 Özellikler

- **📈 Canlı Trend Takibi**: Türkiye'deki güncel trending konuları otomatik olarak çeker
- **🤖 AI Tweet Üretimi**: Google Gemini 2.5 Flash ile  oluşturduğunuz kişilikte tweetler
- **🎭 Akıllı Persona Sistemi**: 3 farklı yazım stili (teknoloji, gündelik, üzgün)
- **⏰ Zamanlanmış Paylaşım**: Saatlik döngüler, optimal etkileşim saatlerinde paylaşım
- **🛡️ Tekrar Önleme**: Konu sınıflandırma önbelleği ve SQLite veritabanı
- **🌐 Web Dashboard**: Gerçek zamanlı bot kontrolü ve monitoring
- **🔒 Güvenlik**: 25/25 güvenlik açığı kapatıldı, production-ready

## 📋 Gereksinimler

- **Python 3.8+**
- **Twitter Developer Account** - [developer.twitter.com](https://developer.twitter.com)
- **Google Gemini API Key** - [ai.google.dev](https://ai.google.dev)

## 🛠️ Kurulum

### Windows (Önerilen)

```batch
# Otomatik kurulum (sanal ortam + bağımlılıklar + veritabanı)
setup.bat

# Bot'u çalıştır (CLI)
start_bot.bat

# Web dashboard (geliştirme)
start_dashboard.bat

# Production sunucu
start_production.bat
```

### Manuel Kurulum

```bash
# Sanal ortam oluştur
python -m venv venv

# Sanal ortamı aktifleştir
# Windows:
venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# Bağımlılıkları yükle
pip install -r requirements.txt

# Veritabanı kurulumu
python database.py
```

## ⚙️ Yapılandırma

`token.env` dosyasını düzenleyerek API anahtarlarınızı ekleyin:

```env
# Twitter API (developer.twitter.com'dan alın)
api_key=YOUR_TWITTER_API_KEY
api_secret=YOUR_TWITTER_API_SECRET
access_token=YOUR_ACCESS_TOKEN
access_token_secret=YOUR_ACCESS_TOKEN_SECRET
bearer_token=YOUR_BEARER_TOKEN
USER_ID=YOUR_TWITTER_USER_ID

# Google Gemini AI (ai.google.dev'den alın)
gemini_api_key=YOUR_GEMINI_API_KEY

# Bot Ayarları (isteğe bağlı)
TRENDS_LIMIT=3
SLEEP_HOURS=1,3,9,10
CYCLE_DURATION_MINUTES=60
GEMINI_MODEL=gemini-2.5-flash
AI_TEMPERATURE=0.85
```

## 🚀 Kullanım

### CLI Bot

```bash
python main.py
```

Bot otomatik olarak:
1. ⏰ Saati kontrol eder (1,3,9,10 saatlerinde paylaşım yapmaz)
2. 📈 Türkiye'den top 3 trend konuyu çeker
3. 🎯 Konuyu sınıflandırır (tech/gündelik/üzgün)
4. ✍️ Uygun persona ile 285 karakterlik tweet oluşturur
5. 🐦 Twitter'a paylaşır ve SQLite'a kaydeder
6. 💤 1 saat bekler ve tekrar eder

### Web Dashboard

```bash
python app.py
```

Dashboard özellikleri:
- 📊 Gerçek zamanlı bot durumu
- 🎛️ Bot başlat/durdur
- 📝 Manuel tweet gönderimi
- 📈 Analitik ve istatistikler
- ⚙️ Canlı yapılandırma editörü

## 🎭 Persona Sistemi

**oluşturduğunuz** kişilik ile 3 farklı yazım stili:

- **Tech** 💻: Özgüvenli, nüktedan teknoloji yorumları
- **Gündelik** 😊: İstanbul'lu, samimi, film referanslı
- **Üzgün** 😢: Empatik, anlayışlı, saygılı ton

## 📊 Örnek Çıktı

```
[+] Trend Konuları Alınıyor...
1. #AIRevolution (45K Tweet) URL: https://twitter.com/search?q=%23AIRevolution
2. #TechTrends (23K Tweet) URL: https://twitter.com/search?q=%23TechTrends
3. #Innovation (18K Tweet) URL: https://twitter.com/search?q=%23Innovation

Tweet Üretiliyor... Konu: #AIRevolution (45K Tweet)
Tweet: AI dalgası gelmiyor—zaten burada. Uyum sağla ya da geride kal. 🚀 #AIRevolution
✅ Tweet başarıyla gönderildi.
[+] Tweet veritabanına kaydedildi.
[+] Bot döngüsü tamamlandı. 1 saat bekleniyor...
```

## 🔒 Güvenlik

✅ **Production Hazır** - 25/25 güvenlik açığı kapatıldı:

- **Thread Safety**: Veritabanı işlemleri için proper locking
- **Input Validation**: Kapsamlı config doğrulama ve temizleme  
- **CSRF Protection**: API endpoints üzerinden güvenli token yönetimi
- **SQL Injection**: Parametreli sorgular ve tablo adı doğrulama
- **Rate Limiting**: Dinamik geri çekilme ve üstel retry mantığı
- **Memory Management**: LRU cache'ler ve kaynak sızıntısı önleme

## 📁 Proje Yapısı

```bash
AI-TwitterPersona/
├── 🤖 Core Bot
│   ├── main.py              # Ana bot döngüsü
│   ├── reply.py             # AI tweet üretimi
│   ├── trend.py             # Trend scraping
│   ├── database.py          # SQLite işlemleri
│   ├── twitter_client.py    # Twitter API
│   └── config.py            # Merkezi yapılandırma
├── 🌐 Web Dashboard  
│   ├── app.py               # Flask web uygulaması
│   ├── production.py        # Production WSGI
│   └── templates/           # HTML şablonları
├── ⚙️ Yapılandırma
│   ├── requirements.txt     # Python bağımlılıkları
│   ├── token.env           # API anahtarları
│   └── gunicorn.conf.py    # Sunucu ayarları
└── 🚀 Windows Scripts
    ├── setup.bat           # Otomatik kurulum
    ├── start_bot.bat       # Bot başlat
    └── start_dashboard.bat # Dashboard başlat
```

## 🧪 Test Komutları

```bash
# Veritabanı testi
python -c "import database; database.createDatabase()"

# Trend çekme testi
python -c "import trend; trends = trend.prepareTrend(3); print(f'{len(trends)} trend bulundu' if trends else 'Trend bulunamadı')"

# AI tweet üretim testi
python -c "import reply; print(reply.generate_reply('yapay zeka'))"

# Twitter client testi
python -c "import twitter_client; client = twitter_client.get_client(); print('Twitter client hazır')"
```

## 📝 Lisans

Bu proje **eğitim amaçlı** geliştirilmiştir. Twitter'ın hizmet şartlarını ihlal etmemek için sorumlu kullanın.

## 🤝 Katkıda Bulunun

1. Bu repo'yu fork edin
2. Özellik branch'i oluşturun (`git checkout -b yeni-ozellik`)
3. Değişikliklerinizi commit edin (`git commit -am 'Yeni özellik eklendi'`)
4. Branch'inizi push edin (`git push origin yeni-ozellik`)
5. Pull Request oluşturun

## ❓ Destek

Sorunlar ve öneriler için [Issues](https://github.com/KilimcininKorOglu/AI-TwitterPersona/issues) sekmesini kullanın.

---

**⚠️ Sorumluluk Reddi**: Bu araç otomatik Twitter paylaşımları yapar. Kullanımından doğacak sorumluluk kullanıcıya aittir. Twitter'ın kullanım şartlarına uygun şekilde kullanın.

**🎯 Hedef Kitle**: Kişisel marka, pazarlama ve teknoloji yaratıcıları için tasarlanmıştır.