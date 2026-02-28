import markdown as md


def _render_html(text: str) -> str:
    return md.markdown(text, extensions=["extra"])


def _strip_markdown(text: str) -> str:
    return text.replace("**", "").replace("*", "").replace("> ", "")


def format_radarr(payload: dict) -> tuple[str, str]:
    movie = payload.get("movie", {})
    title = movie.get("title", "Unknown")
    year = movie.get("year", "")
    is_upgrade = payload.get("isUpgrade", False)

    quality = (
        payload.get("movieFile", {})
        .get("quality", {})
        .get("quality", {})
        .get("name", "Unknown")
    )

    if is_upgrade:
        lines = [
            f"\U0001f3ac **{title}** ({year})",
            f"> \u2b06\ufe0f *Quality upgrade*",
            f"> \U0001f39e\ufe0f Quality: {quality}",
        ]
    else:
        lines = [
            f"\U0001f3ac **{title}** ({year})",
            f"> \u2705 *New addition*",
            f"> \U0001f39e\ufe0f Quality: {quality}",
        ]

    body_md = "\n".join(lines)
    plain = _strip_markdown(body_md)
    html = _render_html(body_md)
    return plain, html


def format_sonarr(payload: dict) -> tuple[str, str]:
    series = payload.get("series", {})
    series_title = series.get("title", "Unknown")
    is_upgrade = payload.get("isUpgrade", False)

    episodes = payload.get("episodes", [{}])
    ep = episodes[0] if episodes else {}
    season = ep.get("seasonNumber", 0)
    episode = ep.get("episodeNumber", 0)
    ep_title = ep.get("title", "")

    quality_field = payload.get("episodeFile", {}).get("quality", {})
    if isinstance(quality_field, dict):
        quality = quality_field.get("quality", {}).get("name", "Unknown")
    else:
        quality = str(quality_field) if quality_field else "Unknown"

    header = f"\U0001f4fa **{series_title}** \u2014 S{season:02d}E{episode:02d}"
    if ep_title:
        header += f" \u2014 *{ep_title}*"

    if is_upgrade:
        lines = [
            header,
            f"> \u2b06\ufe0f *Quality upgrade*",
            f"> \U0001f39e\ufe0f Quality: {quality}",
        ]
    else:
        lines = [
            header,
            f"> \u2705 *New addition*",
            f"> \U0001f39e\ufe0f Quality: {quality}",
        ]

    body_md = "\n".join(lines)
    plain = _strip_markdown(body_md)
    html = _render_html(body_md)
    return plain, html


def format_lidarr(payload: dict) -> tuple[str, str]:
    artist = payload.get("artist", {})
    artist_name = artist.get("name", "Unknown")
    album = payload.get("album", {})
    album_title = album.get("title", "")
    is_upgrade = payload.get("isUpgrade", False)

    track_files = payload.get("trackFiles", [{}])
    tf = track_files[0] if track_files else {}
    quality = (
        tf.get("quality", {})
        .get("quality", {})
        .get("name", "Unknown")
    )

    header = f"\U0001f3b5 **{artist_name}**"
    if album_title:
        header += f" \u2014 *{album_title}*"

    if is_upgrade:
        lines = [
            header,
            f"> \u2b06\ufe0f *Quality upgrade*",
            f"> \U0001f3b5 Format: {quality}",
        ]
    else:
        lines = [
            header,
            f"> \u2705 *New addition*",
            f"> \U0001f3b5 Format: {quality}",
        ]

    body_md = "\n".join(lines)
    plain = _strip_markdown(body_md)
    html = _render_html(body_md)
    return plain, html
