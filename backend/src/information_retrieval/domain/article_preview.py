from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ArticlePreview:
    """Expose only inert metadata so preview clients never receive executable source HTML."""

    title: str | None
    description: str | None
    image_url: str | None
    site_name: str | None
