from app.config.settings import settings
from core.updater import check_for_updates
from ui.app import main

if __name__ == "__main__":
    settings.validate_required()
    main()
