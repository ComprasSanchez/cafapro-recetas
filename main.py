from app.config.settings import settings
from ui.app import main

if __name__ == "__main__":
    settings.validate_required()
    main()
