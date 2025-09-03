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
# Dosyaları sunucuya kopyala
scp -r AI-TwitterPersona/ user@server:/opt/ai-twitterpersona/

# Sunucuda virtual environment ve dependencies
cd /opt/ai-twitterpersona/AI-TwitterPersona
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn eventlet
```

2. **Environment konfigürasyonu:**
```bash
# token.env dosyasını düzenle
cp token.env.example token.env
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
# Service dosyasını düzenle
sudo cp systemd_service.service /etc/systemd/system/ai-twitterpersona.service
sudo nano /etc/systemd/system/ai-twitterpersona.service

# Paths'leri güncelle:
# WorkingDirectory=/opt/ai-twitterpersona/AI-TwitterPersona
# Environment=PATH=/opt/ai-twitterpersona/AI-TwitterPersona/venv/bin
# ExecStart=/opt/ai-twitterpersona/AI-TwitterPersona/venv/bin/gunicorn

# Servisi aktif et
sudo systemctl daemon-reload
sudo systemctl enable ai-twitterpersona
sudo systemctl start ai-twitterpersona
sudo systemctl status ai-twitterpersona
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

# Container çalıştır
docker run -d \
  --name ai-twitterpersona \
  -p 8080:8080 \
  -v $(pwd)/token.env:/app/token.env:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/twitter.db:/app/twitter.db \
  --restart unless-stopped \
  ai-twitterpersona-dashboard
```

#### Docker Compose (Önerilen)
```bash
# Environment ayarla
cp token.env.example token.env
nano token.env  # API keys ve credentials ekle

# Servisleri başlat
docker-compose up -d

# Logları kontrol et
docker-compose logs -f ai-twitterpersona
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

/opt/ai-twitterpersona/AI-TwitterPersona/logs/*.log {
    daily
    missingok
    rotate 52
    compress
    notifempty
    create 644 www-data www-data
}
```

### 2. Health Monitoring
```bash
# Cron job ile health check
crontab -e

# Her 5 dakikada health check
*/5 * * * * curl -f http://localhost:8080/api/status || systemctl restart ai-twitterpersona
```

### 3. Performance Monitoring
- **Grafana + Prometheus** ile metrikleri takip et
- **Uptime monitoring** servisleri kullan (UptimeRobot, Pingdom)
- **Log aggregation** (ELK Stack, Loki)

## 🔧 Maintenance

### 1. Güncelleme
```bash
# Servis durdur
sudo systemctl stop ai-twitterpersona

# Kodu güncelle
cd /opt/ai-twitterpersona/AI-TwitterPersona
git pull origin main

# Dependencies güncelle
source venv/bin/activate
pip install -r requirements.txt

# Servis başlat
sudo systemctl start ai-twitterpersona
```

### 2. Backup
```bash
# Database ve konfigürasyon backup'ı
tar -czf backup-$(date +%Y%m%d).tar.gz token.env twitter.db logs/
```

### 3. Sorun Giderme
```bash
# Servis durumu
sudo systemctl status ai-twitterpersona

# Logları kontrol et
sudo journalctl -u ai-twitterpersona -f

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