#!/usr/bin/env python
"""
Helper script to generate .envs/.production/.django and .envs/.production/.postgres
for hosting SmartShelf without a domain (using your EC2 Public IP address).

Usage:
    python setup_production_env.py <YOUR_EC2_PUBLIC_IP_OR_DOMAIN>
Example:
    python setup_production_env.py 54.210.120.30
"""
from __future__ import annotations

import secrets
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
PRODUCTION_DIR = BASE_DIR / ".envs" / ".production"


def generate_secret(length: int = 50) -> str:
    return secrets.token_urlsafe(length)


def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else None

    if not host:
        print("Tip: You can pass your EC2 Public IP directly: python setup_production_env.py <EC2_IP>")
        entered = input("Enter your EC2 Public IP (or press Enter to allow all hosts '*'): ").strip()
        host = entered if entered else "*"

    PRODUCTION_DIR.mkdir(parents=True, exist_ok=True)

    django_env_path = PRODUCTION_DIR / ".django"
    postgres_env_path = PRODUCTION_DIR / ".postgres"

    # PostgreSQL configuration
    db_name = "smartshelf"
    db_user = "smartshelf_user"
    db_password = generate_secret(32)

    postgres_content = f"""# PostgreSQL Settings
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB={db_name}
POSTGRES_USER={db_user}
POSTGRES_PASSWORD={db_password}
"""

    # Django configuration
    secret_key = generate_secret(50)
    allowed_hosts = f"{host},localhost,127.0.0.1" if host != "*" else "*"
    csrf_origins = f"http://{host},http://localhost,http://127.0.0.1" if host != "*" else "http://localhost,http://127.0.0.1"

    django_content = f"""# Django Settings
DJANGO_SETTINGS_MODULE=config.settings.production
DJANGO_SECRET_KEY={secret_key}
DJANGO_ADMIN_URL=admin/
DJANGO_ALLOWED_HOSTS={allowed_hosts}
DJANGO_CSRF_TRUSTED_ORIGINS={csrf_origins}

# Plain HTTP Mode (for IP-based hosting without a domain)
DJANGO_SECURE_SSL_REDIRECT=False

# Email
DJANGO_DEFAULT_FROM_EMAIL=SmartShelf <noreply@localhost>
DJANGO_SERVER_EMAIL=SmartShelf Server <server@localhost>

# Cache / Redis
REDIS_URL=redis://redis:6379/0

# Docker
USE_DOCKER=yes
IPYTHONDIR=/app/.ipython
"""

    postgres_env_path.write_text(postgres_content)
    django_env_path.write_text(django_content)

    print("\n✅ Successfully generated production environment files:")
    print(f"   - {postgres_env_path}")
    print(f"   - {django_env_path}")
    print(f"\nConfigured Host / IP: {host}")
    print("\nYou can now start your production containers with:")
    print("   docker compose -f docker-compose.production.yml up -d --build\n")


if __name__ == "__main__":
    main()
