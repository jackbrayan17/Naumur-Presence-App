import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from attendance.models import SystemLog


class Command(BaseCommand):
    help = "Create a backup of the SQLite database."

    def handle(self, *args, **options):
        db_path = Path(settings.DATABASES["default"]["NAME"])
        if not db_path.exists():
            self.stdout.write(self.style.ERROR("Database file not found."))
            return

        backups_dir = Path(settings.BASE_DIR) / "backups"
        backups_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = backups_dir / f"backup_{timestamp}.sqlite3"
        shutil.copy2(db_path, backup_path)

        SystemLog.objects.create(
            event_type=SystemLog.EVENT_BACKUP,
            message=f"Database backup created at {backup_path}",
            meta={"backup_path": str(backup_path)},
        )

        self.stdout.write(self.style.SUCCESS(f"Backup created: {backup_path}"))
