# Securing RockTalk with Nginx and SSL

- [Securing RockTalk with Nginx and SSL](#securing-rocktalk-with-nginx-and-ssl)
  - [What We're Building](#what-were-building)
  - [Quick Start (TL;DR)](#quick-start-tldr)
  - [System Architecture](#system-architecture)
  - [Version Information](#version-information)
  - [Important Paths](#important-paths)
  - [Understanding Reverse Proxies](#understanding-reverse-proxies)
  - [Why Use Nginx as a Reverse Proxy?](#why-use-nginx-as-a-reverse-proxy)
  - [Prerequisites](#prerequisites)
  - [Implementation Steps](#implementation-steps)
    - [1. System Preparation](#1-system-preparation)
    - [2. Install Required Software](#2-install-required-software)
    - [3. Configure Firewall](#3-configure-firewall)
    - [4. Install RockTalk](#4-install-rocktalk)
    - [5. Configure Nginx as Reverse Proxy](#5-configure-nginx-as-reverse-proxy)
    - [6. Set Up SSL Encryption](#6-set-up-ssl-encryption)
    - [7. Configure RockTalk for Proxy Environment](#7-configure-rocktalk-for-proxy-environment)
    - [8. Create Systemd Service (Optional but Recommended)](#8-create-systemd-service-optional-but-recommended)
  - [Verification and Testing](#verification-and-testing)
  - [Security Considerations](#security-considerations)
  - [Backup and Restore Procedures](#backup-and-restore-procedures)
    - [Backup Critical Files](#backup-critical-files)
    - [Restore Procedures](#restore-procedures)
    - [Automated Backup Script](#automated-backup-script)
  - [Troubleshooting](#troubleshooting)
  - [Maintenance](#maintenance)

## What We're Building

We're creating a secure gateway for your RockTalk application that:

1. Provides a professional domain name instead of an IP/port
2. Encrypts all traffic with SSL/TLS
3. Handles incoming web traffic efficiently

## Quick Start (TL;DR)

For experienced users who just need the commands:

```sh
# 1. System setup
sudo apt update && sudo apt upgrade -y
sudo apt install nginx certbot python3-certbot-nginx python3 python3-pip -y

# 2. Install RockTalk
pip3 install rocktalk

# 3. Configure Nginx
sudo nano /etc/nginx/sites-available/rocktalk.conf
# [Paste Nginx config from section 5]
sudo ln -s /etc/nginx/sites-available/rocktalk.conf /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default

# 4. SSL setup
sudo certbot --nginx -d <DNS_SERVER_NAME>

# 5. Start services
sudo systemctl restart nginx
rocktalk
```

## System Architecture

```text
User Request Flow:
┌──────────┐    DNS     ┌──────────┐    HTTPS    ┌──────────┐    HTTP    ┌──────────┐
│  Client  │ ─────────> │   DNS    │ ──────────> │  Nginx   │ ─────────> │ RockTalk │
│ Browser  │ <───────── │  Server  │ <─────────  │(443/SSL) │ <────────  │ (8502)   │
└──────────┘            └──────────┘             └──────────┘            └──────────┘
```

## Version Information

This guide has been tested with:

- Ubuntu 20.04.6 LTS
- Nginx 1.18.0
- Python 3.12.8
- Certbot 3.1.0
- RockTalk 0.3.7

## Important Paths

```text
Configuration Files:
├── /etc/nginx/
│   ├── sites-available/rocktalk.conf    # Nginx configuration
│   └── sites-enabled/rocktalk.conf      # Symlink to enabled config
├── /etc/letsencrypt/
│   └── live/<DNS_SERVER_NAME>/          # SSL certificates
├── ~/.rocktalk/.streamlit/
│   └── config.toml                      # Streamlit configuration
└── /etc/systemd/system/
    └── rocktalk.service                 # Systemd service file
```

## Understanding Reverse Proxies

**Regular Proxy (Forward Proxy):**

- Sits in front of **clients** (like a VPN)
- Helps clients reach external services
- Example: Company proxy that lets employees access the internet

```text
Client -> [Proxy] -> Internet
```

**Reverse Proxy (What we're using):**

- Sits in front of **servers**
- Helps route external requests to internal services
- Example: Nginx directing website visitors to your application

```text
Internet -> [Nginx Reverse Proxy] -> RockTalk (Streamlit App)
```

## Why Use Nginx as a Reverse Proxy?

1. **Security:**
   - Hides your internal server structure
   - Provides SSL/TLS encryption
   - Acts as a buffer between internet and your app

2. **Performance:**
   - Handles multiple connections efficiently
   - Can cache content
   - Load balancing capabilities

3. **Flexibility:**
   - Clean URLs (yourdomain.com instead of yourdomain.com:8502)
   - Can route different paths to different services
   - Easier certificate management

## Prerequisites

- **Ubuntu Server**: This guide uses Ubuntu. Adjust commands for other Linux distributions.
- **Root or Sudo Access**: Administrative privileges required.
- **Domain Name**: A registered domain pointing to your server (referred to as `<DNS_SERVER_NAME>`).
- **RockTalk**: Your Streamlit application ready to run locally.

## Implementation Steps

### 1. System Preparation

Update your system:

```sh
sudo apt-get update -y
sudo apt-get upgrade -y
```

### 2. Install Required Software

Install Nginx and SSL tools:

```sh
# Install Nginx
sudo apt install nginx -y

# Install Certbot for SSL certificates
sudo apt install certbot python3-certbot-nginx -y
```

### 3. Configure Firewall

Allow secure web traffic:

```sh
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

### 4. Install RockTalk

Set up Python environment and install RockTalk:

```sh
sudo apt install python3 python3-pip -y
pip3 install rocktalk
```

### 5. Configure Nginx as Reverse Proxy

Create a new configuration file:

```sh
sudo nano /etc/nginx/sites-available/rocktalk.conf
```

Add this configuration (replace `<DNS_SERVER_NAME>` with your domain):

```nginx
server {
    server_name <DNS_SERVER_NAME>;

    # Main application proxy
    location / {
        proxy_pass http://127.0.0.1:8502/;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_redirect off;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # Streamlit-specific WebSocket handling
    location /_stcore/stream {
        proxy_pass http://127.0.0.1:8502/_stcore/stream;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $host;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400;
    }
}
```

Enable the configuration:

```sh
sudo ln -s /etc/nginx/sites-available/rocktalk.conf /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default config
sudo nginx -t  # Test configuration
sudo systemctl reload nginx  # Apply changes
```

### 6. Set Up SSL Encryption

Obtain SSL certificate:

```sh
sudo certbot --nginx -d <DNS_SERVER_NAME>
```

Verify auto-renewal:

```sh
sudo certbot renew --dry-run
```

### 7. Configure RockTalk for Proxy Environment

Create Streamlit configuration:

```sh
mkdir -p ~/.rocktalk/.streamlit/
nano ~/.rocktalk/.streamlit/config.toml
```

Add configuration. These can be changed, just some recommendations that work well in testing.

```toml
[server]
headless = true
enableCORS = false
enableXsrfProtection = false
port = 8502

[browser]
serverAddress = "<DNS_SERVER_NAME>"
serverPort = 443
gatherUsageStats = false
disconnectedSessionTTL = 2592000
```

**Why These Settings Matter:**

1. **Server Settings:**
   - `headless = true`: Runs in server mode without launching a browser
   - `enableCORS = false`: Since Nginx handles routing, we don't need CORS at the app level
   - `enableXsrfProtection = false`: Nginx manages security headers and HTTPS
   - `port = 8502`: Internal port that only Nginx can access (not exposed to internet)

2. **Browser Settings:**
   - `serverAddress`: Tells Streamlit what domain to use for callbacks and WebSocket connections
   - `serverPort = 443`: Uses HTTPS port for secure connections
   - `gatherUsageStats = false`: Disables anonymous usage data collection
   - `disconnectedSessionTTL = 2592000`: Controls how long (in seconds) a disconnected session will be kept alive before being terminated. Here we set 30 days.

These settings optimize RockTalk for running behind a reverse proxy while maintaining security and proper routing through Nginx.

### 8. Create Systemd Service (Optional but Recommended)

Create service file:

```sh
sudo nano /etc/systemd/system/rocktalk.service
```

Add service configuration:

```ini
[Unit]
Description=RockTalk Streamlit Application
After=network.target

[Service]
User=your_username
Group=your_username
WorkingDirectory=/home/your_username/
ExecStart=/usr/bin/env rocktalk
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```sh
sudo systemctl daemon-reload
sudo systemctl enable rocktalk.service
sudo systemctl start rocktalk.service
```

## Verification and Testing

1. Check service status:

    ```sh
    sudo systemctl status rocktalk.service
    ```

2. Verify Nginx status:

    ```sh
    sudo systemctl status nginx
    ```

3. Test your domain:

- Visit `https://<DNS_SERVER_NAME>` in your browser
- Verify SSL padlock is present
- Confirm RockTalk loads correctly

## Security Considerations

1. **Keep Updated:**

    ```sh
    sudo apt update && sudo apt upgrade -y
    ```

2. **Monitor Logs:**

    ```sh
    sudo tail -f /var/log/nginx/error.log  # Nginx errors
    sudo journalctl -u rocktalk.service    # RockTalk service logs
    ```

3. **Additional Security Measures:**

- Consider implementing rate limiting
- Set up fail2ban
- Regular security audits
- Keep backups of configurations

## Backup and Restore Procedures

### Backup Critical Files

Create a backup directory and copy important configurations:

```sh
# Create backup directory
sudo mkdir -p /opt/rocktalk_backup/$(date +%Y%m%d)
cd /opt/rocktalk_backup/$(date +%Y%m%d)

# Backup Nginx configuration
sudo cp /etc/nginx/sites-available/rocktalk.conf ./
sudo cp -r /etc/letsencrypt ./

# Backup Streamlit configuration
cp ~/.rocktalk/.streamlit/config.toml ./

# Backup service file
sudo cp /etc/systemd/system/rocktalk.service ./

# Create archive
sudo tar czf rocktalk_backup_$(date +%Y%m%d).tar.gz *
```

### Restore Procedures

To restore from backup:

```sh
# Extract backup archive
cd /opt/rocktalk_backup/YYYYMMDD
sudo tar xzf rocktalk_backup_YYYYMMDD.tar.gz

# Restore configurations
sudo cp rocktalk.conf /etc/nginx/sites-available/
sudo cp -r letsencrypt/* /etc/letsencrypt/
cp config.toml ~/.rocktalk/.streamlit/
sudo cp rocktalk.service /etc/systemd/system/

# Reload services
sudo systemctl daemon-reload
sudo systemctl restart nginx
sudo systemctl restart rocktalk
```

### Automated Backup Script

Create a backup script `/usr/local/bin/backup-rocktalk.sh`:

```sh
#!/bin/bash
BACKUP_DIR="/opt/rocktalk_backup/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR
cd $BACKUP_DIR

# Backup configurations
sudo cp /etc/nginx/sites-available/rocktalk.conf ./
sudo cp -r /etc/letsencrypt ./
cp ~/.rocktalk/.streamlit/config.toml ./
sudo cp /etc/systemd/system/rocktalk.service ./

# Create archive
sudo tar czf rocktalk_backup_$(date +%Y%m%d).tar.gz *

# Remove files older than 30 days
find /opt/rocktalk_backup -type f -name "*.tar.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_DIR"
```

Make the script executable and schedule it:

```sh
sudo chmod +x /usr/local/bin/backup-rocktalk.sh
sudo crontab -e

# Add this line to run backup daily at 2 AM:
0 2 * * * /usr/local/bin/backup-rocktalk.sh
```

## Troubleshooting

1. **Check Nginx Configuration:**

    ```sh
    sudo nginx -t
    ```

2. **View Logs:**

    ```sh
    sudo journalctl -u nginx
    sudo journalctl -u rocktalk
    ```

3. **Common Issues:**

- Port conflicts: Check if port 8502 is available
- Permission issues: Verify file permissions
- SSL certificate problems: Check Certbot logs

## Maintenance

Regular tasks to keep your setup healthy:

1. Monitor SSL certificate renewal
2. Keep system packages updated
3. Review logs for issues
4. Backup configurations
5. Test your setup periodically

This setup provides a secure, professional way to serve your RockTalk application to users while maintaining good performance and security practices.
