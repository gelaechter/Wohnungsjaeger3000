from datetime import datetime, timedelta

import googlemaps

# Stolen key :P
# https://support.google.com/maps/thread/19784143/5-avenue-de-breteuil-paris-wrong-geoloc?hl=en
gmaps = googlemaps.Client(key='AIzaSyD-1hpguJ8TzcL6V5DJ807Z1u8U-GdSEEQ')


def fetch_transit_time(lat: float, long: float) -> dict[str, int]:
    """
    Fetches the transit time from lat/long to the RUB both by ÖPNV and by car
    """

    # Coming monday at 07:30
    now = datetime.now()
    monday_730 = (now + timedelta(days=7 - now.weekday())).replace(
        hour=7, minute=30, second=0, microsecond=0
    )

    directions_opnv = gmaps.distance_matrix(f"{lat}, {long}",
                                            "Ruhr-Universität Bochum",
                                            mode="transit",
                                            departure_time=monday_730)

    directions_car = gmaps.distance_matrix(f"{lat}, {long}",
                                           "Ruhr-Universität Bochum",
                                           traffic_model="pessimistic",
                                           mode="driving",
                                           departure_time=monday_730)

    directions_bike = gmaps.distance_matrix(f"{lat}, {long}",
                                           "Ruhr-Universität Bochum",
                                           mode="bicycling",
                                           departure_time=monday_730)

    return {
        "minutes_by_opnv": directions_opnv["rows"][0]["elements"][0]["duration"]["value"] // 60,
        "minutes_by_car": directions_car["rows"][0]["elements"][0]["duration"]["value"] // 60,
        "minutes_by_bike": directions_bike["rows"][0]["elements"][0]["duration"]["value"] // 60,
    }
