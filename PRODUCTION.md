# Production Deployment Guide

## Setup

### 1. Generate SSL Certificates

**Option A: Self-Signed (Testing)**
```bash
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/key.pem \
  -out nginx/ssl/cert.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"
```

**Option B: Let's Encrypt (Production)**
```bash
# Install certbot
# Then run:
certbot certonly --webroot -w nginx/certbot \
  -d your-domain.com \
  --email your-email@example.com \
  --agree-tos

# Copy certificates
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem
cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem
```

### 2. Update Configuration

Edit `nginx/nginx.conf`:
- Change `server_name your-domain.com;` to your actual domain
- Adjust rate limiting if needed
- Configure IP whitelisting for MCP server if needed

Edit `.env`:
```bash
# Set a strong API key
BACKEND_API_KEY=your-secure-api-key-here

# Production URLs
MCP_SERVER_URL=http://mcp-server:9003/sse
```

### 3. Deploy

```bash
# Start with production compose file
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check status
docker-compose -f docker-compose.prod.yml ps
```

## Access

All services available through nginx:

- **Frontend**: `https://your-domain.com/`
- **Backend API**: `https://your-domain.com/api/v1/`
- **MCP Server**: `https://your-domain.com/mcp/` (admin only)
- **Health Check**: `https://your-domain.com/health`

## Security

### Firewall Rules

```bash
# Allow only nginx ports
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 8000/tcp  # Block direct backend access
ufw deny 9003/tcp  # Block direct MCP access
ufw deny 3000/tcp  # Block direct frontend access
```

### Secrets Management

Never commit:
- `.env` file
- `nginx/ssl/*.pem`
- `mcp-server/keys/*.json`

Add to `.gitignore`:
```
.env
nginx/ssl/*.pem
!nginx/ssl/.gitkeep
mcp-server/keys/*.json
!mcp-server/keys/.gitkeep
```

### Environment Variables

Store securely:
```bash
# Use Docker secrets or env file
export OPENAI_API_KEY="sk-..."
export BACKEND_API_KEY="strong-random-key"
export GCP_PROJECT_ID="your-project"
```

## Monitoring

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f nginx
docker-compose -f docker-compose.prod.yml logs -f backend
```

### Health Checks
```bash
# Nginx health
curl https://your-domain.com/health

# Backend health
curl https://your-domain.com/api/health

# All containers status
docker-compose -f docker-compose.prod.yml ps
```

## SSL Certificate Renewal

### Let's Encrypt Auto-Renewal
```bash
# Add to crontab
0 0 * * * certbot renew --quiet && \
  cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/cert.pem && \
  cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/key.pem && \
  docker-compose -f docker-compose.prod.yml restart nginx
```

## Scaling

### Horizontal Scaling (Multiple Backend Instances)

Edit `docker-compose.prod.yml`:
```yaml
backend:
  deploy:
    replicas: 3
```

Nginx will automatically load balance across instances.

## Backup

```bash
# Backup volumes
docker run --rm -v forecast-agent_open-webui-data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/webui-data-$(date +%Y%m%d).tar.gz /data

# Backup database (if using external DB)
# Add your DB backup commands here
```

## Troubleshooting

### Check Nginx Config
```bash
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

### SSL Issues
```bash
# Test SSL
openssl s_client -connect your-domain.com:443 -servername your-domain.com

# Check certificate expiry
openssl x509 -in nginx/ssl/cert.pem -noout -dates
```

### Connection Issues
```bash
# Test internal connectivity
docker-compose -f docker-compose.prod.yml exec nginx ping backend
docker-compose -f docker-compose.prod.yml exec backend ping mcp-server
```

## Production Checklist

- [ ] SSL certificates installed
- [ ] Domain name configured
- [ ] Strong `BACKEND_API_KEY` set
- [ ] Firewall rules applied
- [ ] Secrets not in git
- [ ] BigQuery credentials secured
- [ ] Backups configured
- [ ] Monitoring setup
- [ ] Auto-renewal for SSL
- [ ] Rate limiting configured
- [ ] CORS settings reviewed


model=google/embeddinggemma-300m
volume=$PWD/data 

docker run --gpus all -p 8080:80 -v $volume:/data --pull always ghcr.io/huggingface/text-embeddings-inference:1.8 --model-id $model