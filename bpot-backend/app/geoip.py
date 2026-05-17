# ==========================================
# FILE: bpot-backend/routes/geoip.py
# ==========================================

from fastapi import APIRouter, HTTPException, Query
import geoip2.database
import os
import re

router = APIRouter()

# ==============================
# PATHS
# ==============================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

LOGS_DIR = os.path.join(BASE_DIR, "logs")

DB_PATH = os.path.abspath(
    os.path.join(BASE_DIR, "..", "bpot-frontend", "GeoLite2-City.mmdb")
)

# ==============================
# GEOIP LOOKUP
# ==============================

reader = geoip2.database.Reader(DB_PATH)

# ==============================
# HELPERS
# ==============================

def extract_ips(text):
    pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
    matches = re.findall(pattern, text)

    return list(set(matches))


def is_private_ip(ip):
    return (
        ip.startswith("127.")
        or ip.startswith("10.")
        or ip.startswith("192.168.")
        or ip.startswith("172.")
    )


def geo_lookup(ip):
    try:
        response = reader.city(ip)

        return {
            "ip": ip,
            "city": response.city.name,
            "country": response.country.name,
            "country_code": response.country.iso_code,
            "subdivision": (
                response.subdivisions.most_specific.name
                if response.subdivisions
                else None
            ),
            "lat": response.location.latitude,
            "lon": response.location.longitude,
        }

    except Exception:
        return None


# ==========================================
# GET ALL ATTACKS FROM LOGS
# ==========================================

@router.get("/attacks")
async def get_attacks():

    try:
        attacks = []

        files = os.listdir(LOGS_DIR)

        for file in files:

            file_path = os.path.join(LOGS_DIR, file)

            if not os.path.isfile(file_path):
                continue

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            ips = extract_ips(content)

            for ip in ips:

                if is_private_ip(ip):
                    continue

                geo_data = geo_lookup(ip)

                if geo_data:
                    attacks.append(geo_data)

        # Remove duplicates
        unique_attacks = {}

        for attack in attacks:
            unique_attacks[attack["ip"]] = attack

        return list(unique_attacks.values())

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ==========================================
# SINGLE IP LOOKUP
# ==========================================

@router.get("/lookup")
async def lookup_ip(ip: str = Query(...)):

    result = geo_lookup(ip)

    if not result:
        raise HTTPException(
            status_code=404,
            detail="GeoIP data not found"
        )

    return result