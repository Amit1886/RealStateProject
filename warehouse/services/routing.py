from math import radians, sin, cos, sqrt, atan2

from warehouse.models import Warehouse


def _distance_km(lat1, lon1, lat2, lon2):
    r = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


def nearest_dark_store(latitude: float, longitude: float):
    stores = Warehouse.objects.filter(is_dark_store=True, is_active=True, latitude__isnull=False, longitude__isnull=False)
    best = None
    best_distance = None
    for store in stores:
        dist = _distance_km(latitude, longitude, float(store.latitude), float(store.longitude))
        if best is None or dist < best_distance:
            best = store
            best_distance = dist
    return best, best_distance
