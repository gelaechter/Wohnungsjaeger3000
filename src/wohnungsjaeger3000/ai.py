"""
Mistral multimodal API client.

Call a vision-capable Mistral model with a custom prompt and one or more
image URLs. Everything else (model, system prompt, output format, sampling)
is hard-coded for this use case.

Docs:
  - Vision:            https://docs.mistral.ai/studio-api/conversations/vision
  - Chat completions:  https://docs.mistral.ai/studio-api/conversations/chat-completion
  - Model selection:    https://docs.mistral.ai/models/model-selection-guide
  - SDK reference:      https://docs.mistral.ai/resources/sdks

Install:
  pip install mistralai
  export MISTRAL_API_KEY="..."
"""

from __future__ import annotations

import json
from pprint import pprint, pformat
from typing import Any

from mistralai.client import Mistral

# --- Hard-coded configuration ----------------------------------------------

MODEL = "mistral-medium-latest"  # vision-capable per the Model Selection Guide
SYSTEM_PROMPT = (
    "Du sollst dem Nutzer bei der Wohnungssuche in Bochum helfen."
    "Über ihn:"
    " - Er ist Student und will an der Ruhr-Universität-Bochum (RUB) studieren"
    " - Er will dementsprechend nah an der RUB Wohnen"
    "   - Am liebsten <= 30 Minuten mit dem Rad/ÖPNV"
    " - Die Warmmiete sollte 600€ nicht überschreiten"
    "   (hier muss aufgepasst werden weil die Inserate nicht umbedingt perfekte Angaben haben, prüfe also Nebenkosten etc.)"
    ""
    "Du erhälts strukturiertes JSON welches dir Informationen über eine Wohnung liefert."
    "An diesen Informationen und den dazu gehörigen Bildern sollst du die Wohnung bewerten."
)
TEMPERATURE = 0.0  # deterministic
MAX_TOKENS = 1024

RESPONSE_SCHEMA: dict[str, Any] = {
    "properties": {
        "benachrichtigen": {
            "description": "Ob der Nutzer über die Wohnung benachrichtigt werden soll",
            "type": "boolean"
        },
        "nachricht": {
            "description": "Eine kurze Begründung für/gegen die Wohnung",
            "type": "string"
        }
    },
    "required": [
        "benachrichtigen",
        "nachricht"
    ],
    "type": "object"
}

def ask_mistral(prompt: str, image_urls: list[str]) -> dict[str, Any]:
    """Send a custom prompt plus one or more image URLs to a Mistral model.

    Args:
        prompt:     The user message / task text.
        image_urls:  Public image URLs to include in the request.

    Returns:
        The model's text response.
    """
    client = Mistral()  # reads MISTRAL_API_KEY from the environment

    content = [{"type": "text", "text": prompt}]
    for url in image_urls:
        content.append({"type": "image_url", "image_url": url})

    response = client.chat.complete(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "image_analysis",
                "schema": RESPONSE_SCHEMA,
            },
        },
    )

    pprint(response)
    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Example
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    data = {
        'Url': 'https://www.kleinanzeigen.de/s-anzeige/apartment-in-bester-und-zentraler-wohnlage-zu-vermieten-/3488569188-203-2015',
        'Titel': 'Apartment in bester und zentraler Wohnlage zu vermieten!', 'Eingestellt am': '2026-01-18 00:00:00',
        'Beschreibung': '', 'Wohnfläche': '35 m²', 'Zimmer': '1', 'Etage': '1', 'Wohnungstyp': 'Etagenwohnung',
        'Verfügbar ab': 'September 2026', 'Online-Besichtigung': 'Nicht möglich', 'Tauschangebot': 'Kein Tausch',
        'Nebenkosten': '50 €', 'Heizkosten': '123 €', 'Warmmiete': '546 €', 'Kaution / Genoss.-Anteile': '1.120 €',
        'Breitengrad': 51.356522999999996, 'Längengrad': 7.4741372, 'Minuten mit ÖPNV': 64, 'Minuten mit Auto': 30,
        'Minuten mit Fahhrad': 89}

    # images = [
    #     'https://img.kleinanzeigen.de/api/v1/prod-ads/images/41/41dff4fe-9e68-4d8a-b64e-44ed96498e62?rule=$_57.AUTO',
    #     'https://img.kleinanzeigen.de/api/v1/prod-ads/images/a6/a61cefc6-1d8d-49b9-9528-87f914af4d86?rule=$_57.AUTO',
    #     'https://img.kleinanzeigen.de/api/v1/prod-ads/images/66/66c90d17-45cd-496b-b334-683cbd10a43c?rule=$_57.AUTO',
    #     'https://img.kleinanzeigen.de/api/v1/prod-ads/images/2f/2f398983-0a32-4a8c-b007-6a695ca213bc?rule=$_57.AUTO',
    #     'https://img.kleinanzeigen.de/api/v1/prod-ads/images/0e/0e2cec87-1785-4e43-a051-dda71905a34f?rule=$_57.AUTO',
    #     'https://img.kleinanzeigen.de/api/v1/prod-ads/images/30/301cc233-dcbe-4042-a4ac-cbc8fff74457?rule=$_57.AUTO',
    #     'https://img.kleinanzeigen.de/api/v1/prod-ads/images/32/320f63fe-fccf-4154-8f44-572afb8f6d06?rule=$_57.AUTO'];

    answer = ask_mistral(
        prompt=pformat(data),
        image_urls=[]
#         image_urls=images,
    )
    print(answer)
