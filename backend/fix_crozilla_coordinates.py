#!/usr/bin/env python3
"""Fix Crozilla listings - recalculate distances using district centers."""

import os
import math
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

# Supabase connection
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
client = create_client(url, key)

# District coordinates for Varaždin county
DISTRICT_COORDS = {
    "Varaždin": (46.307491, 16.335753),
    "Gornji Kneginec": (46.25051, 16.37555),
    "Ivanec": (46.23333, 16.13333),
    "Klenovnik": (46.27028, 16.07000),
    "Lepoglava": (46.21056, 16.03556),
    "Ludbreg": (46.25000, 16.63333),
    "Maruševec": (46.28262, 16.18539),
    "Novi Marof": (46.16667, 16.33333),
    "Petrijanec": (46.34917, 16.22500),
    "Sračinec": (46.32944, 16.27889),
    "Trnovec Bartolovečki": (46.29472, 16.39889),
    "Varaždinske Toplice": (46.2300, 16.4014),
    "Veliki Bukovec": (46.07800, 16.02225),
    "Visoko": (46.20, 16.15),
    "Hrašćica": (46.25051, 16.37555),
}

DEFAULT_CENTER_LAT = 46.307491
DEFAULT_CENTER_LNG = 16.335753

def get_district_center(district_name: Optional[str]) -> tuple:
    """Get the center coordinates for a district."""
    if not district_name:
        return (DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG)
    
    if district_name in DISTRICT_COORDS:
        return DISTRICT_COORDS[district_name]
    
    district_lower = district_name.lower()
    for name, coords in DISTRICT_COORDS.items():
        if name.lower() == district_lower:
            return coords
    
    for name, coords in DISTRICT_COORDS.items():
        if name.lower() in district_lower or district_lower in name.lower():
            return coords
    
    return (DEFAULT_CENTER_LAT, DEFAULT_CENTER_LNG)

def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points in km."""
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c

def main():
    # Get ALL Crozilla listings with coordinates
    result = client.table("listings_v2").select("id, url, latitude, longitude, location_district, distance_from_center").like("url", "%crozilla%").not_.is_("latitude", "null").execute()
    
    listings = result.data
    print(f"Found {len(listings)} Crozilla listings with coordinates")
    
    updated = 0
    
    for listing in listings:
        listing_id = listing["id"]
        lat = listing.get("latitude")
        lng = listing.get("longitude")
        district = listing.get("location_district")
        old_distance = listing.get("distance_from_center")
        
        if lat is None or lng is None:
            continue
        
        # Calculate distance from listing to ITS DISTRICT center
        center_lat, center_lng = get_district_center(district)
        new_distance = round(haversine_distance(lat, lng, center_lat, center_lng), 2)
        
        # Update if distance changed
        if old_distance != new_distance:
            client.table("listings_v2").update({
                "distance_from_center": new_distance
            }).eq("id", listing_id).execute()
            
            print(f"  ✓ {listing['url'][-25:]}: {old_distance}km → {new_distance}km (to {district or 'Varaždin'})")
            updated += 1
    
    print(f"\n{'='*60}")
    print(f"SUMMARY: Updated {updated} of {len(listings)} listings")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
