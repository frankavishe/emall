# Deploying to the Contabo VPS (mangimall.com)

Production runs as one Docker Compose stack on the VPS: `docker-compose.prod.yml`
(Postgres, MinIO, Django/gunicorn, Next.js) behind Caddy, which gets free HTTPS
certificates from Let's Encrypt automatically.

| Address               | Served by                         |
|-----------------------|-----------------------------------|
| `mangimall.com`       | frontend (Next.js)                |
| `www.mangimall.com`   | redirect to `mangimall.com`       |
| `api.mangimall.com`   | backend API + Django `/admin/`    |
| `media.mangimall.com` | MinIO — product images            |

## 1. DNS (Spaceship)

Domain Manager → `mangimall.com` → Advanced DNS. Four **A** records, all pointing to the
VPS IPv4: hosts `@`, `www`, `api`, `media`. No AAAA records unless they're the VPS's real
IPv6. Check from any machine: `nslookup api.mangimall.com` must return the VPS IP.

## 2. First-time server setup

SSH in as root (IP + password are in the Contabo welcome email):

```bash
ssh root@<VPS_IP>
```

Update the system and create a non-root user:

```bash
apt update && apt upgrade -y
adduser deploy
usermod -aG sudo deploy
```

Firewall — only SSH, HTTP and HTTPS:

```bash
ufw allow OpenSSH
ufw allow 80
ufw allow 443
ufw enable
```

Install Docker and let `deploy` use it:

```bash
curl -fsSL https://get.docker.com | sh
usermod -aG docker deploy
```

Add swap (the Next.js build needs more RAM than small plans have):

```bash
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

Switch to the new user for everything else: `su - deploy`

## 3. Get the code

```bash
git clone https://github.com/frankavishe/emall.git ~/emall
cd ~/emall
git checkout main
```

If the repo is private, GitHub asks for a username + password: use your GitHub username and
a **personal access token** (GitHub → Settings → Developer settings → Personal access tokens,
`repo` read access) as the password.

## 4. Configure secrets

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

Replace every `change-me`:

- `SECRET_KEY`: `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`
- `POSTGRES_PASSWORD`, `MINIO_ROOT_PASSWORD`, `ADMIN_SEED_PASSWORD`: `openssl rand -hex 24`
  (hex only; other characters would break `DATABASE_URL`)
- `ACME_EMAIL`: your real email (Let's Encrypt notices)
- `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` / `DEFAULT_FROM_EMAIL`: your Gmail and a Google
  **App Password**

Save in nano with `Ctrl+O`, Enter, `Ctrl+X`.

## 5. Launch

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

The first build takes several minutes. Watch progress:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend caddy
```

When Caddy logs `certificate obtained successfully` for each domain, open
https://mangimall.com. The admin panel is at https://api.mangimall.com/admin/ (log in with
`ADMIN_SEED_EMAIL` / `ADMIN_SEED_PASSWORD`).

## 6. Deploying updates

```bash
cd ~/emall
git pull
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

Migrations run automatically when the backend starts.

## 7. Backups

The database and images live in Docker volumes (`pgdata`, `miniodata`). Nightly DB dump:

```bash
mkdir -p ~/backups
crontab -e
```

Add this line:

```
0 3 * * * cd ~/emall && docker compose -f docker-compose.prod.yml exec -T db pg_dump -U emall emall | gzip > ~/backups/emall-$(date +\%F).sql.gz
```

Also enable snapshots in the Contabo panel, and copy `~/backups` off the server now and then.

## Troubleshooting

- **HTTPS certificate fails**: DNS isn't pointing at the VPS yet, or ports 80/443 are blocked.
  Check `nslookup`, then `docker compose -f docker-compose.prod.yml restart caddy`.
- **Build killed / out of memory**: make sure swap is on (`free -h`).
- **502 from api.mangimall.com**: `docker compose -f docker-compose.prod.yml logs backend`.
- **Changed a domain**: update `.env.prod` and rebuild with `--build`; the frontend has the
  API URL baked in at build time.
