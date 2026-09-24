# 🤖 AI-TwitterPersona

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Security](https://img.shields.io/badge/security-fixed%2025%2F25-brightgreen.svg)](bugs.md)

Türkiye'nin gerçek zamanlı trend konularını takip eden ve Google Gemini AI ile kişiselleştirilmiş tweetler üreten profesyonel Twitter otomasyon botu.

## ✨ Özellikler

### 🤖 Akıllı Bot Özellikleri

- **📈 Canlı Trend Takibi**: Türkiye'deki güncel trending konuları otomatik çeker
- **🧠 AI Tweet Üretimi**: Google Gemini 2.5 Flash ile doğal, etkileyici tweetler
- **🎭 Dinamik Persona Sistemi**: Konuya uygun 3 farklı yazım stili
- **⏰ Akıllı Zamanlama**: Yapılandırılabilir döngüler ve uyku saatleri
- **🔄 Otomatik Yeniden Deneme**: Hata durumunda akıllı retry mekanizması
- **💾 Önbellek Sistemi**: API çağrılarını minimize eden topic cache

### 🌐 Web Dashboard

- **📊 Gerçek Zamanlı İzleme**: WebSocket ile canlı bot durumu
- **⏱️ Dinamik Geri Sayım**: Sonraki tweet için canlı sayaç
- **🎛️ Tam Kontrol**: Bot başlat/durdur, manuel tweet
- **✨ AI İyileştirme**: Yazılan tweetleri AI ile geliştirme
- **📈 Detaylı Analitik**: Başarı oranları, persona kullanımı, saatlik aktivite
- **🔧 Canlı Konfigurasyon**: Web üzerinden ayarları düzenleme
- **📝 Prompt Editörü**: Persona promptlarını web'den düzenleme

### 🔒 Güvenlik & Stabilite

- **✅ Production Ready**: 25/25 güvenlik açığı kapatıldı
- **🔐 Kimlik Doğrulama**: bcrypt ile güvenli şifreleme
- **🛡️ CSRF Koruması**: Tüm POST endpoint'lerde aktif
- **🔄 Thread Safety**: SQLite için proper locking mekanizması
- **📊 Rate Limiting**: API limitlerini yönetme

## 📋 Sistem Gereksinimleri

| Gereksinim | Versiyon/Detay |
|------------|---------------|
| Python | 3.8+ |
| OS | Windows/Linux/macOS |
| RAM | Minimum 512MB |
| Disk | 100MB boş alan |
| Twitter API | [Developer Account](https://developer.x.com) |
| Gemini API | [Google AI Studio](https://ai.google.dev) |

## 🚀 Hızlı Başlangıç

### Windows Otomatik Kurulum (Önerilen)

```batch
# 1. Tam kurulum (venv + dependencies + database)
setup.bat

# 2. API anahtarlarını token.env dosyasına ekleyin

# 3. Bot'u başlatın
start_bot.bat

# 4. Dashboard'u açın (opsiyonel)
start_dashboard.bat
```

### Manuel Kurulum

```bash
# 1. Repository'yi klonlayın
git clone https://github.com/KilimcininKorOglu/AI-TwitterPersona.git
cd AI-TwitterPersona

# 2. Sanal ortam oluşturun ve aktifleştirin
python -m venv venv
# Windows:
venv\Scripts\activate.bat
# Linux/Mac:
source venv/bin/activate

# 3. Bağımlılıkları yükleyin
pip install -r requirements.txt

# 4. Veritabanını oluşturun
python database.py

# 5. token.env dosyasını yapılandırın (aşağıya bakın)

# 6. Bot'u başlatın
python main.py

# 7. Web Dashboard (opsiyonel)
python app.py
```

## ⚙️ Yapılandırma

### token.env Dosyası

`token.env` dosyası oluşturun ve aşağıdaki bilgileri ekleyin:

```env
# ============ ZORUNLU AYARLAR ============

# Twitter API Credentials
# https://developer.x.com/en/portal/dashboard adresinden alın
api_key=YOUR_TWITTER_API_KEY
api_secret=YOUR_TWITTER_API_SECRET
access_token=YOUR_ACCESS_TOKEN
access_token_secret=YOUR_ACCESS_TOKEN_SECRET
bearer_token=YOUR_BEARER_TOKEN
USER_ID=YOUR_TWITTER_USER_ID  # https://tweeterid.com

# Google Gemini API
# https://ai.google.dev adresinden alın
gemini_api_key=YOUR_GEMINI_API_KEY

# ============ BOT AYARLARI (Opsiyonel) ============

# Trend Ayarları
TRENDS_URL=https://xtrends.iamrohit.in/turkey
TRENDS_LIMIT=5

# Zamanlama (saat formatında)
SLEEP_HOURS=1,2,3,4,5,6  # Bot'un uyuyacağı saatler
CYCLE_DURATION_MINUTES=30  # Tweet atma aralığı

# AI Model Ayarları
GEMINI_MODEL=gemini-2.5-flash
AI_TEMPERATURE=1.0
AI_TOP_P=0.9
AI_TOP_K=40

# ============ WEB DASHBOARD (Opsiyonel) ============

# Flask Ayarları
FLASK_SECRET_KEY=your-very-secure-secret-key-here
WEB_HOST=127.0.0.1
WEB_PORT=5000
WEB_DEBUG=False

# Admin Girişi
ADMIN_USERS=admin
ADMIN_PASSWORD=admin123  # İlk girişte değiştirin!
```

## 🎮 Kullanım

### CLI Bot Modu

```bash
python main.py
```

Bot başlatıldığında:

1. ⏰ Saat kontrolü yapar (uyku saatleri dışında)
2. 📊 Türkiye trendlerini çeker
3. 🎯 Konuyu AI ile sınıflandırır
4. ✍️ Uygun persona ile tweet oluşturur
5. 📤 Twitter'a gönderir
6. 💾 Veritabanına kaydeder
7. ⏳ 30 dakika bekler ve tekrarlar

### Web Dashboard

```bash
python app.py
# Tarayıcıda: http://localhost:5000
```

#### Dashboard Özellikleri

| Sayfa | URL | Özellikler |
|-------|-----|------------|
| **Ana Sayfa** | `/` | Bot durumu, istatistikler, geri sayım |
| **Tweet Geçmişi** | `/tweets` | Tüm tweetler, filtreleme, yeniden gönderme |
| **Manuel Tweet** | `/manual` | AI destekli tweet oluşturma |
| **İzleme** | `/monitoring` | Gerçek zamanlı konsol, API durumu |
| **Analitik** | `/analytics` | Grafikler, başarı oranları |
| **Ayarlar** | `/config` | Canlı konfigurasyon düzenleme |
| **Prompt Editörü** | `/prompts` | Persona promptlarını düzenleme |

## 🎭 Persona Sistemi

Bot, konuya göre otomatik olarak 3 farklı persona kullanır:

### 💻 Tech Persona

- **Kullanım**: Teknoloji, bilim, inovasyon konuları
- **Stil**: Özgüvenli, analitik, vizyoner
- **Örnek**: "AI revolution isn't coming—it's here. Adapt or get left behind 🚀"

### 😊 Casual Persona

- **Kullanım**: Gündelik, eğlence, sosyal konular
- **Stil**: Samimi, eğlenceli, İstanbul vurgusu
- **Örnek**: "Pazartesi sendromu hitting different ya... Kahve sayısı 3'ü geçti ☕"

### 😔 Sad Persona

- **Kullanım**: Üzücü haberler, felaketler, ciddi konular
- **Stil**: Empatik, saygılı, teselli edici
- **Örnek**: "Başımız sağ olsun... Güçlü kalmaya devam 🙏"

## 📊 Örnek Konsol Çıktısı

```
[+] Bot başlatılıyor...
[+] Twitter client hazır
[+] Gemini AI bağlandı
[+] Veritabanı hazır

[10:30:00] Trend konuları alınıyor...
  1. #YapayZeka (45K Tweet)
  2. #Teknoloji (23K Tweet)
  3. #İnovasyon (18K Tweet)

[10:30:05] Seçilen konu: #YapayZeka
[10:30:06] AI sınıflandırması: tech
[10:30:08] Tweet üretildi (275/280 karakter)
[10:30:10] ✅ Tweet başarıyla gönderildi!
[10:30:11] Veritabanına kaydedildi (ID: 42)

⏳ Sonraki tweet: 30 dakika (11:00:00)
29:59... 29:58... 29:57...
```

## 🧪 Test ve Doğrulama

```bash
# Bileşen testleri
python -c "import database; database.createDatabase()"  # DB testi
python -c "import trend; print(trend.prepareTrend(3))"  # Trend testi
python -c "import twitter_client; twitter_client.get_client()"  # API testi

# Konfigurasyon doğrulama
python -c "from app import test_twitter_length_calculation; test_twitter_length_calculation()"

# Türkçe karakter testi
python -c "from trend import test_turkish_character_filtering; test_turkish_character_filtering()"
```

## 🚀 Production Deployment

### Gunicorn ile Deployment

```bash
# ÖNEMLİ: Sadece tek worker kullanın!
gunicorn --config gunicorn.conf.py app:app --workers=1
```

### Systemd Service

Bot, dashboard içinden başlatılır ve durdurulur. `main.py` dosyasını ayrı bir servis olarak çalıştırmayın; iki bot aynı anda tweet atar.

```bash
# Dashboard service
sudo cp twitter-dashboard.service /etc/systemd/system/
sudo systemctl enable twitter-dashboard
sudo systemctl start twitter-dashboard
```

### Docker Deployment

```bash
# Build & Run
docker-compose up -d

# Logları izle
docker-compose logs -f
```

## 📁 Proje Yapısı

```
AI-TwitterPersona/
├── 🤖 Core Bot Logic
│   ├── main.py              # Ana bot döngüsü ve zamanlama
│   ├── reply.py             # AI tweet üretimi ve persona yönetimi
│   ├── trend.py             # Trend topic scraping
│   ├── twitter_client.py    # Twitter API client
│   └── database.py          # SQLite veritabanı işlemleri
│
├── 🌐 Web Interface
│   ├── app.py               # Flask + SocketIO application
│   ├── templates/
│   │   ├── dashboard.html   # Ana kontrol paneli
│   │   ├── manual.html      # Manuel tweet sayfası
│   │   ├── monitoring.html  # Gerçek zamanlı izleme
│   │   └── analytics.html   # İstatistik grafikleri
│   └── static/
│       ├── js/app.js        # WebSocket ve AJAX
│       └── css/style.css    # Custom stiller
│
├── ⚙️ Configuration
│   ├── config.py            # Merkezi konfigurasyon yönetimi
│   ├── token.env            # API keys ve ayarlar (gitignore)
│   ├── requirements.txt     # Python bağımlılıkları
│   └── topic_cache.json     # AI sınıflandırma cache
│
├── 🚀 Deployment
│   ├── production.py        # WSGI production config
│   ├── gunicorn.conf.py     # Gunicorn ayarları
│   ├── Dockerfile           # Container image
│   ├── docker-compose.yml   # Multi-service orchestration
│   └── *.service           # Systemd unit files
│
└── 📝 Documentation
    ├── README.md            # Bu dosya
    ├── CLAUDE.md           # Claude Code için rehber
    └── bugs.md             # Güvenlik analizi
```

## 🔧 Sorun Giderme

| Sorun | Çözüm |
|-------|-------|
| **Twitter 401 Hatası** | API anahtarlarını kontrol edin, permissions'ı "Read and Write" yapın |
| **Gemini API Hatası** | API key'i ve kotanızı kontrol edin |
| **Trend Çekme Hatası** | xtrends.iamrohit.in sitesinin erişilebilir olduğunu kontrol edin |
| **Database Locked** | Tek bir bot instance'ı çalıştığından emin olun |
| **WebSocket Bağlanmıyor** | Flask app'in çalıştığından ve port 5000'in açık olduğundan emin olun |

## 📝 Lisans

MIT License - Detaylar için [LICENSE](LICENSE) dosyasına bakın.

## 🤝 Katkıda Bulunma

1. Fork edin (`https://github.com/KilimcininKorOglu/AI-TwitterPersona/fork`)
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Değişikliklerinizi commit edin (`git commit -m 'Add amazing feature'`)
4. Branch'e push edin (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 🙏 Teşekkürler

- [Google Gemini AI](https://ai.google.dev) - AI tweet üretimi
- [Twitter API v2](https://developer.x.com) - Tweet gönderimi
- [Flask](https://flask.palletsprojects.com) - Web dashboard
- [Socket.IO](https://socket.io) - Gerçek zamanlı iletişim

## ⚠️ Sorumluluk Reddi

Bu araç eğitim amaçlı geliştirilmiştir. Twitter'ın kullanım şartlarına uygun kullanım kullanıcının sorumluluğundadır. Otomatik tweet gönderimi yaparken:

- Twitter'ın rate limit'lerine uyun
- Spam içerik üretmeyin
- Yanıltıcı veya zararlı içerik paylaşmayın
- Platform kurallarına saygı gösterin

## 📞 İletişim & Destek

- **Issues**: [GitHub Issues](https://github.com/KilimcininKorOglu/AI-TwitterPersona/issues)
- **Discussions**: [GitHub Discussions](https://github.com/KilimcininKorOglu/AI-TwitterPersona/discussions)

---

**Developed with ❤️ using Claude AI**
