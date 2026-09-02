import re
from datetime import datetime, date, timedelta
from os.path import basename
from pprint import pformat
from textwrap import dedent
from typing import Any
from urllib.parse import urlparse

from patchright.async_api import Page
from scrapling.engines._browsers._stealth import AsyncStealthySession
from scrapling.engines.static import FetcherSession
from scrapling.spiders import Spider, Response

from wohnungsjaeger3000.ai import ask_mistral
from wohnungsjaeger3000.db import already_seen, add_to_seen
from wohnungsjaeger3000.gmaps import fetch_transit_time
from wohnungsjaeger3000.notify import send_notification


def parse_datetime(date_str: str) -> datetime:
    """Parsed kleinanzeigen datestrings als datetime"""
    match date_str:
        # Today
        case value if value.startswith("Heute"):
            time_part = datetime.strptime(value.split(", ")[1], "%H:%M").time()
            return datetime.combine(date.today(), time_part)
        # Yesterday
        case value if value.startswith("Gestern"):
            time_part = datetime.strptime(value.split(", ")[1], "%H:%M").time()
            yesterday = date.today() - timedelta(days=1)
            return datetime.combine(yesterday, time_part)
        # Raw date
        case _:
            return datetime.strptime("18.01.2026", "%d.%m.%Y")


def image_max_url(url: str) -> str:
    """
    Found in Image Max URL user script:
        var queries = get_queries(src);
	    queries.rule = queries.rule.replace(/\\d+/, "57");
    """
    return re.sub(
        # Replace the digits in the rule query parameter
        r"(rule=[^&]*?)(\d+)",
        # with 57
        r"\g<1>57",
        url,
        count=1,
    )


def get_last_path(url: str) -> str:
    """
    https://gnu.org/what/is/a/man
        -> man
    https://fvcxljnn.com/image.jpg
        -> image.jpg
    """
    return basename(urlparse(url).path.rstrip("/"))


def weigh_and_notify(data: Any, images: list[str]) -> dict[str, Any]:
    response = ask_mistral(
        prompt=pformat(data),
        image_urls=images
    )
    if response["benachrichtigen"]:
        send_notification(data["Url"], response["nachricht"], images=images)
    return response


class WohnungsSpider(Spider):
    name = "Wohnungen"
    # Sucht Wohnungen (gebote) in Bochum (+30km) bis 500€
    start_urls = ["https://www.kleinanzeigen.de/s-bochum/anzeige:angebote/preis::500/wohnung/k0l1932r30"]
    concurrent_requests = 3
    autothrottle_enabled = True

    async def wait_for_description(self, page: Page):
        await page.wait_for_function(dedent("""\
                                        () => {
                                            const el = document.querySelector('#viewad-description-text');
                                            return el && el.innerText.trim().length > 0;
                                        }
                                    """),
                                     polling=1000)

    def configure_sessions(self, manager):
        # Fast HTTP for listing pages (default)
        manager.add("http", FetcherSession())

        # Stealth browser so we don't get fucked by bot detection
        # Additionally await fully loading the description
        manager.add("anzeige", AsyncStealthySession(
            headless=True,
            network_idle=True,
            capture_xhr=r"https://www\.kleinanzeigen\.de/s-anzeige/.*",
            page_action=self.wait_for_description
        ))

    async def parse(self, response: Response):
        # Find all Anzeigen on the page
        for anzeige in response.find_all("article"):
            data = {}
            anzeigen_url = anzeige.attrib["data-href"]
            id = get_last_path(anzeigen_url)

            # Skip already seen Anzeigen
            if already_seen(id):
                self.logger.info(f"Skipping Anzeige: {id}")
                continue

            # Set date
            date_element = anzeige.css('svg[data-title="calendarOutline"] + span')[0].get_all_text().clean()

            if date_element is not None:
                data["Eingestellt am"] = parse_datetime(date_element).isoformat(sep=" ")
            # Follow the anzeige and parse it
            yield response.follow(anzeigen_url, callback=self.parse_anzeige, meta={"data": data})
            add_to_seen(id)

    async def parse_anzeige(self, response: Response):
        data = response.meta["data"]
        images = []

        # Set url
        url = response.url
        data["Url"] = url

        # Download images
        for bild in response.css("#viewad-image"):
            bild_url = bild.attrib["src"]
            max_res_url = image_max_url(bild_url)
            images.append(max_res_url)

        # Set title
        data["Titel"] = response.css("#viewad-title")[0].get_all_text(ignore_tags=("span",)).clean()

        # Set date
        if "Eingestellt am" not in data:
            date_raw = response.css("i.icon-calendar-gray-simple + span")[0].get_all_text()
            data["Eingestellt am"] = parse_datetime(date_raw).isoformat(sep=" ")

        # Set description
        data["Beschreibung"] = response.css("#viewad-description-text")[0].get_all_text().clean()

        # Set additional details
        for detail in response.css(".addetailslist--detail"):
            detail_title = detail.get_all_text(ignore_tags=("span",)).clean()
            detail_value = detail.find("span").get_all_text().clean()
            data[detail_title] = detail_value

        # Set checklist
        for checktag in response.css(".checktag"):
            data[checktag.get_all_text()] = True

        # Set location
        lat_raw = response.css('meta[property="og:latitude"]')[0].attrib["content"]
        long_raw = response.css('meta[property="og:longitude"]')[0].attrib["content"]
        lat = float(lat_raw)
        long = float(long_raw)
        data["Breitengrad"] = lat
        data["Längengrad"] = long

        # Fetch transit time
        transit_calc = fetch_transit_time(lat, long)
        data["Minuten mit ÖPNV"] = transit_calc["minutes_by_opnv"]
        data["Minuten mit Auto"] = transit_calc["minutes_by_car"]
        data["Minuten mit Fahhrad"] = transit_calc["minutes_by_bike"]

        # Let AI check the data and notify me
        response = weigh_and_notify(data, [])
        data["Benachrichtigt"] = response["benachrichtigen"]
        data["Begründung"] = response["nachricht"]
        yield data


def scrape_data():
    result = WohnungsSpider().start()
    print(f"Scraped {len(result.items)} Wohnungen")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result.items.to_csv(f"./output/wohnungen_{timestamp}.csv")
