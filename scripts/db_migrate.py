import os
import sys
from alembic.config import Config
from alembic import command

def main() -> int:
    """
    Uso:
      python scripts/db_migrate.py dev upgrade head
      python scripts/db_migrate.py prod stamp head
      python scripts/db_migrate.py dev revision "baseline"  (autogenerate)
      python scripts/db_migrate.py dev current
      python scripts/db_migrate.py prod heads
    """
    if len(sys.argv) < 3:
        print("Uso: db_migrate.py <dev|prod> <command> [args...]")
        return 2

    env = sys.argv[1].lower().strip()
    cmd = sys.argv[2].lower().strip()
    args = sys.argv[3:]

    cfg = Config("alembic.ini")

    # Pasamos env a env.py vía x-arg
    cfg.cmd_opts = type("opts", (), {"x": [f"env={env}"]})()

    # Validar URL
    if env == "dev":
        url = os.getenv("DATABASE_URL_DEV")
    elif env == "prod":
        url = os.getenv("DATABASE_URL_PROD")
    else:
        url = os.getenv("DATABASE_URL")

    if not url:
        raise SystemExit("Falta DATABASE_URL_DEV / DATABASE_URL_PROD (o DATABASE_URL)")

    # Comandos
    if cmd == "upgrade":
        rev = args[0] if args else "head"
        command.upgrade(cfg, rev)
    elif cmd == "stamp":
        rev = args[0] if args else "head"
        command.stamp(cfg, rev)
    elif cmd == "revision":
        if not args:
            raise SystemExit('Falta mensaje. Ej: python scripts/db_migrate.py dev revision "baseline"')
        message = args[0]
        command.revision(cfg, message=message, autogenerate=True)
    elif cmd == "current":
        command.current(cfg)
    elif cmd == "heads":
        command.heads(cfg)
    elif cmd == "history":
        command.history(cfg)
    else:
        raise SystemExit("Comando inválido: upgrade|stamp|revision|current|heads|history")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())