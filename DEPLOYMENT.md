# Deploying to Your Own Ubuntu VPS

This project ships with a production-ready Docker setup (`Dockerfile` +
`docker-compose.yml`: Postgres, Redis, gunicorn, Celery worker/beat). The
fastest, most reliable path to a live URL on a bare Ubuntu VPS is Docker
Compose + Nginx as a reverse proxy + Let's Encrypt for TLS. Total time: ~20
minutes on a fresh VPS.

## 0. Requirements

- An Ubuntu 22.04/24.04 VPS with a public IP, reachable over SSH.
- A domain (or subdomain) with an `A` record pointing at the VPS's IP.
  (You can also deploy without a domain, over plain `http://ip:8000`, and
  skip the Nginx/TLS steps — see "No-domain quickstart" at the bottom.)

## 1. SSH in and install Docker

```bash
ssh your_user@your_vps_ip

sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker   # or log out/in
docker --version
docker compose version
```

## 2. Clone the repo

```bash
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>
```

## 3. Configure production secrets

```bash
cp .env.prod.example .env.prod
nano .env.prod
```

At minimum, set:

- `SECRET_KEY` — generate one: `python3 -c "import secrets; print(secrets.token_urlsafe(64))"`
- `ALLOWED_HOSTS` — e.g. `yourdomain.com,www.yourdomain.com` (or the bare
  VPS IP if you're not using a domain yet)
- `POSTGRES_PASSWORD` and the matching `DATABASE_URL`
- `DEFAULT_FROM_EMAIL` / `SERVER_EMAIL` and, ideally, a real
  `EMAIL_BACKEND` (Mailgun via Anymail is pre-installed) so password
  reset/registration emails actually deliver. Without this, emails just
  get logged to the container's stdout, which is fine for a demo but not
  for real users.

## 4. Build and start the stack

```bash
docker compose up -d --build
docker compose logs -f web   # watch it come up; Ctrl+C to stop watching
```

The `web` service automatically runs `migrate` and `collectstatic` on
startup (see `docker-compose.yml`), so the database schema and static
files (Tailwind CSS, JS, images) are ready on first boot.

## 5. Create your first Admin-role user

Registration always creates a `Member` by default (by design — see the
README). Promote your own account after signing up through the site:

```bash
docker compose exec web python manage.py set_user_role you@example.com admin
```

Optionally also create a Django-admin superuser (separate from the app's
"Admin" role, and only needed for `/admin/`):

```bash
docker compose exec web python manage.py createsuperuser
```

At this point the app is reachable at `http://your_vps_ip:8000`.

## 6. Put Nginx + HTTPS in front of it (recommended)

```bash
sudo apt install -y nginx certbot python3-certbot-nginx
```

Create `/etc/nginx/sites-available/yourdomain`:

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/yourdomain /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

Certbot edits the Nginx config to redirect to HTTPS and sets up
auto-renewal. Your app is now live at `https://yourdomain.com`.

Since the app now runs behind a TLS-terminating proxy, make sure
`USE_HTTPS_IN_ABSOLUTE_URLS=True` is set in `.env.prod` (it is, by
default in `.env.prod.example`) so password-reset/confirmation links use
`https://`.

## 7. Day-2 operations

```bash
# Redeploy after a git pull
git pull
docker compose up -d --build

# Tail logs
docker compose logs -f web
docker compose logs -f celery

# Run a one-off management command
docker compose exec web python manage.py <command>

# Back up the database
docker compose exec db pg_dump -U postgres django_template > backup.sql
```

## No-domain quickstart

If you just want a URL to submit quickly and don't have a domain yet:

1. Follow steps 1–5 above.
2. Open port 8000 in your firewall: `sudo ufw allow 8000/tcp`
3. Your live URL is `http://your_vps_ip:8000`.

This skips TLS, so avoid it for anything beyond a demo/review — browsers
will also block some PWA installability checks over plain HTTP (they
require HTTPS, `localhost` being the only exception), so add the domain +
Nginx + certbot steps above when you're ready to show off the install
prompt / offline support.
