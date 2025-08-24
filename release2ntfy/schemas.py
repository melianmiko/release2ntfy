from typing import List

from pydantic import BaseModel, Field


class EventSourceConfig(BaseModel):
    id: str
    template: str = ""

    url: str = ""
    headers: dict = {}
    title: str = "New release $ID, $REVISION"
    revision_path: str = "version"
    description_path: str = "description"
    preview_url_path: str = "html_url"

    valid_status: int = 200
    index_mode: str = "first_match"
    revision_regexp: str | None = None


class NtfyTargetConfig(BaseModel):
    topic: str
    base_url: str = "https://ntfy.sh"
    icon_tag: str = "newspaper"
    no_verify: bool = False


class AppConfig(BaseModel):
    cron_schedule: str = "0 16 * * *"
    target: NtfyTargetConfig
    events: List[EventSourceConfig] = Field(default_factory=lambda: [])
    env: dict = {}


class ReleaseInfo(BaseModel):
    id: str
    title: str
    revision: str
    description: str
    preview_url: str

    prev_revision: str = ""
    notify: bool = False
