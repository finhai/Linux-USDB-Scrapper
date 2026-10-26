"""Validated, atomic non-secret application preferences."""

import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path


class SettingsError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    storage_root: str = str(Path.home() / "Music" / "UltraStar")
    concurrency: int = 2
    sort_field: str = "id"
    sort_direction: str = "asc"
    remember: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.storage_root, str) or not Path(self.storage_root).is_absolute():
            raise SettingsError("Choose an absolute library location")
        if type(self.concurrency) is not int or not 1 <= self.concurrency <= 8:
            raise SettingsError("Download concurrency must be between 1 and 8")
        if self.sort_field not in (
            "id",
            "interpret",
            "title",
            "genre",
            "year",
            "edition",
            "golden",
            "language",
            "autor",
            "rating",
            "views",
            "lastchange",
        ) or self.sort_direction not in ("asc", "desc"):
            raise SettingsError("Invalid default sort")
        if type(self.remember) is not bool:
            raise SettingsError("Invalid remember-credentials preference")


def settings_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
    return base / "usdb-scrapper" / "settings.json"


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or settings_path()

    def load(self) -> Settings:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return Settings(**data)
        except FileNotFoundError:
            return Settings()
        except (OSError, ValueError, TypeError):
            raise SettingsError("Settings could not be read; defaults are being used") from None

    def save(self, settings: Settings) -> None:
        temporary: str | None = None
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.path.parent, delete=False
            ) as stream:
                temporary = stream.name
                json.dump(asdict(settings), stream, indent=2)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
        except OSError:
            raise SettingsError("Settings could not be saved") from None
        finally:
            if temporary is not None:
                Path(temporary).unlink(missing_ok=True)
