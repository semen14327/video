# 🚀 ГАЙД ПО ДЕПЛОЮ Watch Together 2.0

---

## 📋 ЧТО НУЖНО:

### **1. VPS Сервер:**
```
Минимум:
• 1 CPU
• 2GB RAM
• 20GB SSD
• Ubuntu 22.04+

Цена: $5-10/мес

Где купить:
• DigitalOcean
• Hetzner
• Vultr
```

### **2. Домен (опционально):**
```
Примеры:
• watchtogether.com
• yourname.com

Где купить:
• Namecheap
• Cloudflare
• Reg.ru

Цена: $10/год
```

---

## 🛠️ УСТАНОВКА НА VPS:

### **Шаг 1: Подключение**
```bash
ssh root@ваш-ip
```

### **Шаг 2: Обновление системы**
```bash
apt update
apt upgrade -y
```

### **Шаг 3: Установка Python**
```bash
apt install python3 python3-pip python3-venv -y
```

### **Шаг 4: Установка Nginx**
```bash
apt install nginx -y
```

### **Шаг 5: Загрузка проекта**
```bash
cd /var/www
mkdir watchtogether
cd watchtogether

# Загрузить файлы (через scp или git)
```

### **Шаг 6: Виртуальное окружение**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### **Шаг 7: Тест локально**
```bash
python main.py

# Должно быть:
# 🚀 Watch Together запущен!
# 📺 Открой: http://localhost:8000

# Ctrl+C для остановки
```

---

## 🔧 НАСТРОЙКА NGINX:

### **Создать конфиг:**
```bash
nano /etc/nginx/sites-available/watchtogether
```

### **Вставить:**
```nginx
server {
    listen 80;
    server_name ваш-домен.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### **Активировать:**
```bash
ln -s /etc/nginx/sites-available/watchtogether /etc/nginx/sites-enabled/
nginx -t
systemctl restart nginx
```

---

## 🔒 SSL СЕРТИФИКАТ (HTTPS):

### **Установить Certbot:**
```bash
apt install certbot python3-certbot-nginx -y
```

### **Получить сертификат:**
```bash
certbot --nginx -d ваш-домен.com
```

### **Автообновление:**
```bash
certbot renew --dry-run
```

---

## 🔄 АВТОЗАПУСК (systemd):

### **Создать сервис:**
```bash
nano /etc/systemd/system/watchtogether.service
```

### **Вставить:**
```ini
[Unit]
Description=Watch Together Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/watchtogether
Environment="PATH=/var/www/watchtogether/venv/bin"
ExecStart=/var/www/watchtogether/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### **Активировать:**
```bash
systemctl daemon-reload
systemctl enable watchtogether
systemctl start watchtogether
systemctl status watchtogether
```

### **Команды:**
```bash
# Статус
systemctl status watchtogether

# Перезапуск
systemctl restart watchtogether

# Логи
journalctl -u watchtogether -f
```

---

## 📱 ИНТЕГРАЦИЯ С TELEGRAM:

### **1. Создать бота:**
```
@BotFather → /newbot
Получить токен
```

### **2. Создать WebApp:**
```
@BotFather → /newapp
Выбрать бота
Название: Watch Together
Short name: watchtogether
URL: https://ваш-домен.com
```

### **3. Добавить кнопку:**
```
/setmenu
Выбрать бота

Текст кнопки: 🎬 Смотреть вместе
WebApp URL: https://ваш-домен.com
```

### **4. Создать комнату с параметром:**
```
https://ваш-домен.com?room=dota2
https://ваш-домен.com?room=anime_room
```

---

## 🔥 ОПТИМИЗАЦИЯ:

### **1. Увеличить лимиты:**
```bash
nano /etc/security/limits.conf

# Добавить:
* soft nofile 65536
* hard nofile 65536
```

### **2. Настроить Firewall:**
```bash
ufw allow 22
ufw allow 80
ufw allow 443
ufw enable
```

### **3. Мониторинг:**
```bash
# Использование ресурсов
htop

# Логи в реальном времени
journalctl -u watchtogether -f
```

---

## 📊 МАСШТАБИРОВАНИЕ:

### **Для 1000+ юзеров:**

```
1. Увеличить VPS:
   • 4GB RAM
   • 2 CPU

2. Добавить Redis:
   apt install redis-server
   
3. Использовать Gunicorn:
   gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

4. Настроить Load Balancer (опционально)
```

---

## 🐛 РЕШЕНИЕ ПРОБЛЕМ:

### **Ошибка: "Address already in use"**
```bash
# Найти процесс
lsof -i :8000

# Убить
kill -9 PID
```

### **WebSocket не работает:**
```
Проверить Nginx конфиг:
• proxy_http_version 1.1
• proxy_set_header Upgrade
• proxy_set_header Connection "upgrade"
```

### **YouTube не загружается:**
```
Проблема: видео заблокировано владельцем
Решение: использовать .mp4 ссылки
```

---

## ✅ ЧЕКЛИСТ ДЕПЛОЯ:

- [ ] VPS куплен
- [ ] Домен настроен (опционально)
- [ ] Python установлен
- [ ] Nginx установлен
- [ ] Проект загружен
- [ ] Зависимости установлены
- [ ] Nginx настроен
- [ ] SSL сертификат получен
- [ ] systemd сервис создан
- [ ] Telegram бот создан
- [ ] WebApp подключен
- [ ] Тестирование пройдено

---

## 🎯 ГОТОВО!

**Ваш сервис работает на:**
```
https://ваш-домен.com
https://ваш-домен.com/gallery
```

**Поделитесь ссылкой и зовите друзей!** 🚀
