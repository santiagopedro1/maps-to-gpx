#!/usr/bin/env python3
"""
maps_to_gpx.py — Convert a Google Maps directions URL to a road-following GPX file.

Usage:
    python maps_to_gpx.py "<google_maps_url>" [output.gpx] [options]

Requirements:
    pip install requests python-dotenv

API key is read from a .env file in the current directory:
    MAPS_API_KEY=your_key_here

Get a key at:
    https://console.cloud.google.com/apis/library/directions-backend.googleapis.com
"""

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs, unquote

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests python-dotenv")

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("Missing dependency: pip install requests python-dotenv")


# ── Polyline decoder ──────────────────────────────────────────────────────────

def decode_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a Google encoded polyline into a list of (lat, lon) tuples."""
    coords, index, lat, lng = [], 0, 0, 0
    while index < len(encoded):
        for is_lng in (False, True):
            result, shift, b = 0, 0, 0x20
            while b >= 0x20:
                b = ord(encoded[index]) - 63
                index += 1
                result |= (b & 0x1F) << shift
                shift += 5
            delta = ~(result >> 1) if result & 1 else result >> 1
            if is_lng:
                lng += delta
            else:
                lat += delta
        coords.append((lat / 1e5, lng / 1e5))
    return coords


# ── Google Maps URL parser ────────────────────────────────────────────────────

def parse_maps_url(url: str) -> list[str]:
    """
    Extract waypoints from a Google Maps URL.
    Handles formats like:
      /maps/dir/Origin/Waypoint1/Destination
      /maps/dir/?api=1&origin=...&destination=...&waypoints=...
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    # New-style (?api=1&origin=...&destination=...)
    if "origin" in qs and "destination" in qs:
        waypoints = [qs["origin"][0]]
        if "waypoints" in qs:
            waypoints += qs["waypoints"][0].split("|")
        waypoints.append(qs["destination"][0])
        return waypoints

    # Classic /maps/dir/A/B/C path style
    path = unquote(parsed.path)
    match = re.search(r"/maps/dir/(.+)", path)
    if match:
        # Filter out the viewport segment (@lat,lon,zoomz) and empty parts
        parts = [p for p in match.group(1).split("/") if p and not p.startswith("@")]
        if len(parts) >= 2:
            return parts

    sys.exit(
        "Could not parse waypoints from URL.\n"
        "Make sure you copy the full URL from Google Maps after getting directions."
    )


# ── Directions API call ───────────────────────────────────────────────────────

def get_route(waypoints: list[str], api_key: str, mode: str) -> list[tuple[float, float]]:
    """Call the Directions API and return decoded route coordinates."""
    origin      = waypoints[0]
    destination = waypoints[-1]
    via         = waypoints[1:-1]

    params = {
        "origin":      origin,
        "destination": destination,
        "mode":        mode,
        "key":         api_key,
    }
    if via:
        params["waypoints"] = "|".join(via)

    resp = requests.get(
        "https://maps.googleapis.com/maps/api/directions/json",
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    if data["status"] != "OK":
        sys.exit(f"Directions API error: {data['status']} — {data.get('error_message', '')}")

    # Collect all step polylines across all legs
    coords: list[tuple[float, float]] = []
    for leg in data["routes"][0]["legs"]:
        for step in leg["steps"]:
            coords.extend(decode_polyline(step["polyline"]["points"]))

    return coords


# ── GPX writer ────────────────────────────────────────────────────────────────

def build_gpx(coords: list[tuple[float, float]], name: str) -> str:
    """Build a GPX string from a list of (lat, lon) coordinates."""
    root = ET.Element("gpx", {
        "version": "1.1",
        "creator": "maps_to_gpx.py",
        "xmlns":              "http://www.topografix.com/GPX/1/1",
        "xmlns:xsi":          "http://www.w3.org/2001/XMLSchema-instance",
        "xsi:schemaLocation": (
            "http://www.topografix.com/GPX/1/1 "
            "http://www.topografix.com/GPX/1/1/gpx.xsd"
        ),
    })

    meta = ET.SubElement(root, "metadata")
    ET.SubElement(meta, "name").text = name
    ET.SubElement(meta, "time").text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    trk = ET.SubElement(root, "trk")
    ET.SubElement(trk, "name").text = name
    trkseg = ET.SubElement(trk, "trkseg")

    for lat, lon in coords:
        ET.SubElement(trkseg, "trkpt", {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}"})

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    load_dotenv()
    api_key = os.getenv("MAPS_API_KEY")
    if not api_key:
        sys.exit(
            "MAPS_API_KEY not found.\n"
            "Create a .env file in the current directory with:\n"
            "  MAPS_API_KEY=your_key_here"
        )

    parser = argparse.ArgumentParser(
        description="Convert a Google Maps URL to a road-following GPX file."
    )
    parser.add_argument("url",    help="Google Maps directions URL")
    parser.add_argument("output", nargs="?", default="route.gpx", help="Output GPX file (default: route.gpx)")
    parser.add_argument("--mode", default="driving",
                        choices=["driving", "walking", "bicycling", "transit"],
                        help="Travel mode (default: driving)")
    parser.add_argument("--name", default="My Route", help="Track name in the GPX file")
    args = parser.parse_args()

    print("Parsing URL …")
    waypoints = parse_maps_url(args.url)
    print(f"  Found {len(waypoints)} waypoints: {' → '.join(waypoints)}")

    print("Fetching route from Directions API …")
    coords = get_route(waypoints, api_key, args.mode)
    print(f"  Got {len(coords)} track points")

    print(f"Writing {args.output} …")
    gpx = build_gpx(coords, args.name)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(gpx)

    print(f"Done! Saved to {args.output}")


if __name__ == "__main__":
    main()