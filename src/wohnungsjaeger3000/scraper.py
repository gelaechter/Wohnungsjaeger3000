import re
from datetime import datetime, date, timedelta
from os.path import basename
from pathlib import Path
from urllib.parse import urlparse

import googlemaps
from scrapling.engines._browsers._stealth import AsyncStealthySession
from scrapling.spiders import Spider, Response


def parse_datetime(date_str: str) -> datetime:
    """Parsed kleinanzeigen datestrings als datetime"""
    match date_str:
        case value if value.startswith("Heute"):
            time_part = datetime.strptime("18:30", "%H:%M").time()
            return datetime.combine(date.today(), time_part)
        case value if value.startswith("Gestern"):
            time_part = datetime.strptime("18:30", "%H:%M").time()
            yesterday = date.today() - timedelta(days=1)
            return datetime.combine(yesterday, time_part)
        case _:
            return datetime.strptime("18.01.2026", "%d.%m.%Y")


def image_max_url(url: str) -> str:
    """
    Found in Image Max URL user script:
        var queries = get_queries(src);
	    queries.rule = queries.rule.replace(/\d+/, "57");
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
    https://fvcxljnn/image.jpg
        -> image.jpg
    """
    return basename(urlparse(url).path.rstrip("/"))


# Stolen key :P
# https://support.google.com/maps/thread/19784143/5-avenue-de-breteuil-paris-wrong-geoloc?hl=en
gmaps = googlemaps.Client(key='AIzaSyD-1hpguJ8TzcL6V5DJ807Z1u8U-GdSEEQ')


def fetch_transit_time(lat: float, long: float) -> int:
    """
    Fetches the transit time from lat/long to the RUB both by ÖPNV and by car
    """
    now = datetime.now()

    monday_730 = (
            now - timedelta(days=now.weekday())
    ).replace(hour=7, minute=30, second=0, microsecond=0)

    directions_opnv = gmaps.distance_matrix(f"{lat}, {long}",
                                            "Ruhr-Universität Bochum",
                                            mode="transit",
                                            departure_time=monday_730)

    directions_car = gmaps.distance_matrix(f"{lat}, {long}",
                                           "Ruhr-Universität Bochum",
                                           mode="driving",
                                           departure_time=monday_730)

    return {
        "minutes_by_opnv": directions_opnv["rows"][0]["elements"][0]["duration"]["value"] / 60,
        "minutes_by_car": directions_car["rows"][0]["elements"][0]["duration"]["value"] / 60,
    }


class WohnungsSpider(Spider):
    name = "Wohnungen"
    # Sucht Wohnungen in Bochum (+30km) bis 500€
    start_urls = ["https://www.kleinanzeigen.de/s-bochum/preis::500/wohnung/k0l1932r30"]
    concurrent_requests = 3
    autothrottle_enabled = True

    def configure_sessions(self, manager):
        # Stealth browser so we don't get fucked by bot detection
        manager.add("stealth", AsyncStealthySession(
            headless=True,
            network_idle=True,
        ))

    async def parse(self, response: Response):
        # Find all Anzeigen on the page
        for anzeige in response.find_all("article"):
            data = {}
            anzeigen_url = anzeige.attrib["data-href"]

            # Set date
            date_element = anzeige.css('svg[data-title="calendarOutline"] + span').get()

            if date_element is not None:
                data["eingestellt_am"] = parse_datetime(date_element.text)
            # Follow the anzeige and parse it
            yield response.follow(anzeigen_url, callback=self.parse_anzeige, meta={"data": data})
            return

        # Finally go to the next page
        naechste_seite = response.css('a[title="Nächste"]').get().attrib['href']
        yield response.follow(naechste_seite)

    async def parse_anzeige(self, response: Response):
        data = response.meta["data"]

        # Set url
        url = response.url
        data["url"] = url

        # Set id
        data["id"] = get_last_path(url)

        # Download images
        for bild in response.css(".galleryimage-element img"):
            bild_url = bild.attrib["src"]
            max_res_url = image_max_url(bild_url)
            # Follow the image to download it
            yield response.follow(max_res_url, callback=self.download_image, meta={"id": data["id"]})

        # Set title
        data["title"] = response.css("#viewad-title")

        # Set date
        date: datetime
        if not data["eingestellt_am"]:
            date_element = response.css("i.icon-calendar-gray-simple + span").get()
            data["eingestellt_am"] = parse_datetime(date_element.text)

        # Set description
        data["beschreibung"] = response.css("#viewad-description-text").get_all_text()

        # Set additional details
        for detail in response.css(".addetailslist--detail").get_all():
            detail_title = detail.text
            detail_value = detail.find("span").text
            data[detail_title] = detail_value

        # Set checklist
        for checktag in response.css(".checktag").get_all():
            data[checktag.text] = True

        # Set location
        lat_raw = response.css('meta[property="og:latitude"').get().attrib["content"]
        long_raw = response.css('meta[property="og:longitude"').get().attrib["content"]
        lat = float(lat_raw)
        long = float(long_raw)
        data["latitude"] = lat
        data["longitude"] = long

        # Fetch transit time
        transit_calc = fetch_transit_time(lat, long)
        data["time_by_opnv"] = transit_calc["minutes_by_opnv"]
        data["time_by_car"] = transit_calc["minutes_by_car"]

        yield data

    async def download_image(self, response: Response):
        anzeigen_id = response.meta["id"]
        filename = get_last_path(response.url)
        # Determine output folder
        output_folder = Path("./images") / anzeigen_id
        output_folder.mkdir(parents=True, exist_ok=True)
        # Write image
        with open(file=output_folder / filename, mode="wb") as f:
            f.write(response.body)


def main():
    result = WohnungsSpider().start()
    print(f"Scraped {len(result.items)} Wohnungen")
    result.items.to_csv("wohnungen.csv")


if __name__ == '__main__':
    main()
