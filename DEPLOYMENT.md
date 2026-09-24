# AI-TwitterPersona Dashboard - Deployment Guide

Bu dokuman AI-TwitterPersona Dashboard'u production ortamında deploy etmek için gereken tüm adımları içerir.

## 🚀 Production Deployment Seçenekleri

### 1. Manuel Deployment (Linux Server)

#### Gereksinimler

```bash
# Python 3.11+ ve pip
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv nginx

# Virtual environment oluştur
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn eventlet
```

#### Adımlar

1. **Sunucuya deployment:**

```bash
# Dosyaları sunucuya kopyala (servis dosyaları /opt/ai-twitterpersona yolunu bekler)
scp -r AI-TwitterPersona/ user@server:/tmp/AI-TwitterPersona
ssh user@server
sudo mv /tmp/AI-TwitterPersona /opt/ai-twitterpersona
sudo chown -R "$USER" /opt/ai-twitterpersona

# Sunucuda virtual environment ve dependencies
cd /opt/ai-twitterpersona
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn eventlet
```

2. **Environment konfigürasyonu:**

```bash
# token.env dosyasını düzenle
cp .env.example token.env
nano token.env

# Gerekli değerleri gir:
# - Twitter API credentials
# - Gemini API key
# - ADMIN_PASSWORD değiştir
# - WEB_HOST=0.0.0.0
# - WEB_PORT=8080
# - WEB_DEBUG=False
```

3. **Systemd servis kurulumu:**

```bash
# Servis twitterbot kullanıcısı ile /opt/ai-twitterpersona dizininden çalışır
sudo useradd --create-home --shell /bin/bash twitterbot
sudo chown -R twitterbot:twitterbot /opt/ai-twitterpersona
sudo cp twitter-dashboard.service /etc/systemd/system/twitter-dashboard.service

# Servisi aktif et
sudo systemctl daemon-reload
sudo systemctl enable twitter-dashboard
sudo systemctl start twitter-dashboard
sudo systemctl status twitter-dashboard
```

4. **Nginx reverse proxy:**

```bash
# Nginx konfigürasyonu
sudo nano /etc/nginx/sites-available/ai-twitterpersona

# Aşağıdaki konfigürasyonu ekle:
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 86400;
    }
}

# Site'ı aktif et
sudo ln -s /etc/nginx/sites-available/ai-twitterpersona /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. Docker Deployment

#### Basit Docker

```bash
# Image build et
docker build -t ai-twitterpersona-dashboard .

# token.env mevcut olmalı ve container kullanıcısı (UID 1000) tarafından yazılabilir olmalı,
# çünkü ayarlar sayfası değişiklikleri bu dosyaya kaydeder
sudo chown 1000:1000 token.env

# Container çalıştır (veritabanı ve loglar named volume içinde tutulur)
docker run -d \
  --name ai-twitterpersona \
  -p 8080:8080 \
  -e WEB_HOST=0.0.0.0 -e WEB_PORT=8080 \
  -e DB_NAME=/app/data/twitter.db -e TOPIC_CACHE_FILE=/app/data/topic_cache.json \
  -v $(pwd)/token.env:/app/token.env \
  -v ai_twitterpersona_logs:/app/logs \
  -v ai_twitterpersona_data:/app/data \
  --restart unless-stopped \
  ai-twitterpersona-dashboard
```

#### Docker Compose (Önerilen)

```bash
# Environment ayarla
cp .env.example token.env
nano token.env  # API keys ve credentials ekle
sudo chown 1000:1000 token.env  # Container kullanıcısı yazabilsin

# Servisleri başlat
docker compose up -d

# Opsiyonel nginx reverse proxy (./nginx.conf ve ./ssl/ gerekir)
docker compose --profile nginx up -d

# Logları kontrol et
docker compose logs -f ai-twitterpersona
```

### 3. Cloud Deployment

#### Heroku

```bash
# Heroku CLI kurulu olmalı
heroku create ai-twitterpersona-dashboard

# Environment variables ayarla
heroku config:set \
  TWITTER_API_KEY=your_key \
  GEMINI_API_KEY=your_key \
  ADMIN_PASSWORD=secure_password

# Deploy et
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

#### AWS/DigitalOcean/VPS

- Docker Compose dosyasını kullan
- Load balancer ve auto-scaling için kubernetes kullan
- Database için managed PostgreSQL kullan

## 🔒 Güvenlik Konfigürasyonu

### 1. SSL/TLS (HTTPS)

```bash
# Let's Encrypt ile SSL sertifikası
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Otomatik renewal
sudo systemctl enable certbot.timer
```

### 2. Güvenlik Headers

```nginx
# Nginx'e ekle
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
```

### 3. Firewall

```bash
# UFW ile port yönetimi
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

## 📊 Monitoring ve Logging

### 1. Log Management

```bash
# Log rotasyonu
sudo nano /etc/logrotate.d/ai-twitterpersona

/opt/ai-twitterpersona/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    notifempty
    create 644 twitterbot twitterbot
}
```

### 2. Health Monitoring

```bash
# Cron job ile health check
crontab -e

# Her 5 dakikada health check
*/5 * * * * curl -f http://localhost:8080/api/status || systemctl restart twitter-dashboard
```

### 3. Performance Monitoring

- **Grafana + Prometheus** ile metrikleri takip et
- **Uptime monitoring** servisleri kullan (UptimeRobot, Pingdom)
- **Log aggregation** (ELK Stack, Loki)

## 🔧 Maintenance

### 1. Güncelleme

```bash
# Servis durdur
sudo systemctl stop twitter-dashboard

# Kodu güncelle
cd /opt/ai-twitterpersona
sudo -u twitterbot git pull origin main

# Dependencies güncelle
source venv/bin/activate
pip install -r requirements.txt

# Servis başlat
sudo systemctl start twitter-dashboard
```

### 2. Backup

```bash
# Database ve konfigürasyon backup'ı
tar -czf backup-$(date +%Y%m%d).tar.gz token.env twitter.db logs/
```

### 3. Sorun Giderme

```bash
# Servis durumu
sudo systemctl status twitter-dashboard

# Logları kontrol et
sudo journalctl -u twitter-dashboard -f

# Application logları
tail -f logs/twitter_bot.log
tail -f logs/gunicorn_error.log
```

## ⚡ Performance Optimizasyonu

### 1. Database

- SQLite yerine PostgreSQL kullan (çoklu user için)
- Database indexleri ekle
- Connection pooling aktif et

### 2. Caching

- Redis ile session ve cache yönetimi
- CDN kullan (CloudFlare, AWS CloudFront)

### 3. Load Balancing

- Nginx ile load balancing
- Multi-instance deployment
- Auto-scaling konfigürasyonu

## 🆘 Troubleshooting

### Sık Karşılaşılan Problemler

1. **503 Service Unavailable**
   - Gunicorn worker'ları kontrol et
   - Memory/CPU kullanımını kontrol et

2. **WebSocket Connection Failed**
   - Nginx proxy ayarlarını kontrol et
   - Firewall kurallarını kontrol et

3. **Database Locked**
   - SQLite file permissions kontrol et
   - Multiple process conflict kontrolü

4. **API Rate Limits**
   - Twitter/Gemini API limitlerini kontrol et
   - Request frequency azalt

Bu deployment guide ile Twitter Bot Dashboard'u production ortamında güvenli ve stable şekilde çalıştırabilirsiniz.
