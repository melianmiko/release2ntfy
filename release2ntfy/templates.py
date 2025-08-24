import urllib.parse

from release2ntfy.schemas import EventSourceConfig


def gitea_release(e: EventSourceConfig) -> EventSourceConfig:
    parts = urllib.parse.urlparse(e.url)

    e.title = f"{parts.hostname}: Release {parts.path}, $REVISION"
    e.url = f"{parts.scheme}://{parts.hostname}/api/v1/repos{parts.path}/releases/latest"
    e.revision_path = "name"
    e.description_path = "body"
    e.preview_url_path = "html_url"

    return e


def donationalerts_alerts(e: EventSourceConfig) -> EventSourceConfig:
    return EventSourceConfig(
        id=e.id,
        url="https://www.donationalerts.com/api/v1/alerts/donations",
        headers={ "Authorization": "Bearer $DONATION_ALERTS_SECRET" },
        index_mode="all",
        title="DonationAlerts: New donation",
        revision_path="data[$INDEX].id",
        description_path="data[$INDEX].message",
    )

KNOWN_TEMPLATES = {
    "gitea_release": gitea_release,
    "donationalerts_alerts": donationalerts_alerts,
}
