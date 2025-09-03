# AI-TwitterPersona Dashboard - Deployment Guide

This document contains all the necessary steps to deploy the AI-TwitterPersona Dashboard in a production environment.

## 🚀 Production Deployment Options

### 1. Manual Deployment (Linux Server)

#### Requirements
```bash
# Python 3.11+ and pip
sudo apt update
sudo apt install python3.11 python3.11-pip python3.11-venv nginx

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn eventlet
```

#### Steps
1. **Server deployment:**
```bash
# Copy files to server
scp -r AI-TwitterPersona/ user@server:/opt/ai-twitterpersona/

# Virtual environment and dependencies on server
cd /opt/ai-twitterpersona/AI-TwitterPersona
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install gunicorn eventlet
```

2. **Environment configuration:**
```bash
# Edit token.env file
cp token.env.example token.env
nano token.env

# Enter required values:
# - Twitter API credentials
# - Gemini API key
# - Change ADMIN_PASSWORD
# - WEB_HOST=0.0.0.0
# - WEB_PORT=8080
# - WEB_DEBUG=False
```

3. **Systemd service setup:**
```bash
# Edit service file
sudo cp systemd_service.service /etc/systemd/system/ai-twitterpersona.service
sudo nano /etc/systemd/system/ai-twitterpersona.service

# Update paths:
# WorkingDirectory=/opt/ai-twitterpersona/AI-TwitterPersona
# Environment=PATH=/opt/ai-twitterpersona/AI-TwitterPersona/venv/bin
# ExecStart=/opt/ai-twitterpersona/AI-TwitterPersona/venv/bin/gunicorn

# Enable service
sudo systemctl daemon-reload
sudo systemctl enable ai-twitterpersona
sudo systemctl start ai-twitterpersona
sudo systemctl status ai-twitterpersona
```

4. **Nginx reverse proxy:**
```bash
# Nginx configuration
sudo nano /etc/nginx/sites-available/ai-twitterpersona

# Add the following configuration:
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

# Enable site
sudo ln -s /etc/nginx/sites-available/ai-twitterpersona /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 2. Docker Deployment

#### Simple Docker
```bash
# Build image
docker build -t ai-twitterpersona-dashboard .

# Run container
docker run -d \
  --name ai-twitterpersona \
  -p 8080:8080 \
  -v $(pwd)/token.env:/app/token.env:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/twitter.db:/app/twitter.db \
  --restart unless-stopped \
  ai-twitterpersona-dashboard
```

#### Docker Compose (Recommended)
```bash
# Setup environment
cp token.env.example token.env
nano token.env  # Add API keys and credentials

# Start services
docker-compose up -d

# Check logs
docker-compose logs -f ai-twitterpersona
```

### 3. Cloud Deployment

#### Heroku
```bash
# Heroku CLI must be installed
heroku create ai-twitterpersona-dashboard

# Set environment variables
heroku config:set \
  TWITTER_API_KEY=your_key \
  GEMINI_API_KEY=your_key \
  ADMIN_PASSWORD=secure_password

# Deploy
git add .
git commit -m "Deploy to Heroku"
git push heroku main
```

#### AWS/DigitalOcean/VPS
- Use Docker Compose file
- Use Kubernetes for load balancing and auto-scaling
- Use managed PostgreSQL for database

## 🔒 Security Configuration

### 1. SSL/TLS (HTTPS)
```bash
# SSL certificate with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Automatic renewal
sudo systemctl enable certbot.timer
```

### 2. Security Headers
```nginx
# Add to Nginx
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header X-XSS-Protection "1; mode=block";
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
```

### 3. Firewall
```bash
# Port management with UFW
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

## 📊 Monitoring and Logging

### 1. Log Management
```bash
# Log rotation
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
# Health check with cron job
crontab -e

# Health check every 5 minutes
*/5 * * * * curl -f http://localhost:8080/api/status || systemctl restart ai-twitterpersona
```

### 3. Performance Monitoring
- Track metrics with **Grafana + Prometheus**
- Use **Uptime monitoring** services (UptimeRobot, Pingdom)
- **Log aggregation** (ELK Stack, Loki)

## 🔧 Maintenance

### 1. Updates
```bash
# Stop service
sudo systemctl stop ai-twitterpersona

# Update code
cd /opt/ai-twitterpersona/AI-TwitterPersona
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Start service
sudo systemctl start ai-twitterpersona
```

### 2. Backup
```bash
# Database and configuration backup
tar -czf backup-$(date +%Y%m%d).tar.gz token.env twitter.db logs/
```

### 3. Troubleshooting
```bash
# Service status
sudo systemctl status ai-twitterpersona

# Check logs
sudo journalctl -u ai-twitterpersona -f

# Application logs
tail -f logs/twitter_bot.log
tail -f logs/gunicorn_error.log
```

## ⚡ Performance Optimization

### 1. Database
- Use PostgreSQL instead of SQLite (for multi-user)
- Add database indexes
- Enable connection pooling

### 2. Caching
- Redis for session and cache management
- Use CDN (CloudFlare, AWS CloudFront)

### 3. Load Balancing
- Load balancing with Nginx
- Multi-instance deployment
- Auto-scaling configuration

## 🆘 Troubleshooting

### Common Issues

1. **503 Service Unavailable**
   - Check Gunicorn workers
   - Check memory/CPU usage

2. **WebSocket Connection Failed**
   - Check Nginx proxy settings
   - Check firewall rules

3. **Database Locked**
   - Check SQLite file permissions
   - Check multiple process conflicts

4. **API Rate Limits**
   - Check Twitter/Gemini API limits
   - Reduce request frequency

With this deployment guide, you can run the Twitter Bot Dashboard securely and stably in a production environment.