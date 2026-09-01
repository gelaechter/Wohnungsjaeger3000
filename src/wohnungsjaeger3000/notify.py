import requests


def send_notification(anzeigen_url, beschreibung):
    topic_url = "https://ntfy.adminforge.de//d404051dc43bdf5e798ac97370df595e"
    template = (f"Neue [Wohnung]({anzeigen_url})\n"
                f"---\n"
                f"{beschreibung}")

    response = requests.post(
        topic_url,
        data=template.encode("utf-8"),
        headers={
            "Title": "Neue Wohnung!",
            "Markdown": "yes",
        },
        timeout=10,
    )

    response.raise_for_status()
