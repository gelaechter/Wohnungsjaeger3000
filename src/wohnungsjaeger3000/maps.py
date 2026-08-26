from pprint import pprint

import googlemaps
from datetime import datetime

# Stolen key :P
# https://support.google.com/maps/thread/19784143/5-avenue-de-breteuil-paris-wrong-geoloc?hl=en
gmaps = googlemaps.Client(key='AIzaSyD-1hpguJ8TzcL6V5DJ807Z1u8U-GdSEEQ')

# Request directions via public transit
now = datetime.now()
directions_result = gmaps.distance_matrix("51.44340678988347, 7.2098923448901155",
                                              "Ruhr-Universität Bochum",
                                              mode="transit",
                                              departure_time=now)

pprint(directions_result)
