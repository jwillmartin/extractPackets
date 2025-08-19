#!/usr/bin/env python3
import json
import math
import os
import tkinter as tk
from tkinter import filedialog
from pathlib import Path

try:
    import folium
except ImportError:
    raise SystemExit("Please install folium: pip install folium")

R_EARTH = 6378137.0  # meters

def select_json_file():
    """
    Open a file dialog to select a JSON file.

    Returns
    -------
    json_path : str
        Path to the selected CSV file or an empty string if cancelled.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    json_path = filedialog.askopenfilename(
        title="Select TIM Payload JSON",
        filetypes=[("JSON files", "*.json")]
    )
    return json_path

def to_deg(val) -> float:
    """
    Auto-scale J2735 1e-7 degree ints to float degrees.

    Parameters
    ----------
    val : int | float
        The value to convert.

    Returns
    -------
    float
        The converted value in degrees.
    """
    if isinstance(val, (int, float)):
        if abs(val) > 180:
            return float(val) / 1e7
        return float(val)
    raise ValueError("Latitude/longitude must be numeric")

def ll_delta_to_deg(d: dict) -> tuple[float, float]:
    """
    Convert a node-LL delta dict to (dlat_deg, dlon_deg).

    Parameters
    ----------
    d : dict
        The delta dictionary containing "lat" and "lon" keys.

    Returns
    -------
    tuple[float, float]
        The converted latitude and longitude deltas in degrees.
    """
    lat = d.get("lat")
    lon = d.get("lon")
    if lat is None or lon is None:
        raise ValueError("LL delta missing lat/lon")
    return (float(lat) / 1e7, float(lon) / 1e7)

def xy_delta_to_meters(d: dict) -> tuple[float, float]:
    """
    Convert a node-XY delta to (dx_m east, dy_m north).

    Parameters
    ----------
    d : dict
        The delta dictionary containing "x" and "y" keys.

    Returns
    -------
    tuple[float, float]
        The converted x and y deltas in meters.
    """
    x = d.get("x")
    y = d.get("y")
    if x is None or y is None:
        raise ValueError("XY delta missing x/y")
    dx = float(x)
    dy = float(y)

    # Return meters
    return dx / 100.0, dy / 100.0

def apply_xy_delta(lat_deg: float, lon_deg: float, dx_m: float, dy_m: float) -> tuple[float, float]:
    """
    Apply local east/north meters to lat/lon degrees.

    Parameters
    ----------
    lat_deg : float
        The latitude in degrees.
    lon_deg : float
        The longitude in degrees.
    dx_m : float
        The change in x (east) in meters.
    dy_m : float
        The change in y (north) in meters.

    Returns
    -------
    tuple[float, float]
        The new latitude and longitude in degrees.
    """
    lat_rad = math.radians(lat_deg)
    dlat = (dy_m / R_EARTH) * (180.0 / math.pi)
    dlon = (dx_m / (R_EARTH * math.cos(max(1e-12, abs(lat_rad))))) * (180.0 / math.pi)
    # Preserve sign with original hemisphere
    if lat_deg < 0:
        dlat = -abs(dlat) if dy_m < 0 else abs(dlat)
    if lon_deg < 0:
        dlon = -abs(dlon) if dx_m < 0 else abs(dlon)
    return lat_deg + dlat, lon_deg + dlon

def extract_regions(data: dict):
    """
    Get values from the TIM message across all regions.

    i.e., name, anchor lat/long, path offsets, delta type 
    """
    frames = data.get("value", {}).get("dataFrames", [])
    for df in frames:
        content_obj = df.get("content", {}) or {}
        content_key = None
        name = ""
        if isinstance(content_obj, dict) and content_obj:
            # Get content type, e.g., 'advisory', 'workZone', etc.
            content_key = str(next(iter(content_obj.keys())))
            name = content_key

        # Get region information
        regions = df.get("regions", []) or []
        for reg in regions:
            # Get lat/long anchor point
            anchor = reg.get("anchor", {})
            lat = to_deg(anchor.get("lat"))
            long = to_deg(anchor.get("long"))

            # Get node offsets
            desc = reg.get("description", {})
            path = desc.get("path", {})
            offset = path.get("offset", {})
            delta_type = None
            nodes = []
            if "ll" in offset:
                delta_type = "ll"
            elif "xy" in offset:
                delta_type = "xy"
            nodes = offset[delta_type].get("nodes", [])
            yield name, lat, long, nodes, delta_type

def build_path_points(anchor_lat: float, anchor_long: float, nodes: list, delta_type: str) -> list[tuple[float, float]]:
    """
    Return list of (lat, long) from nodes.

    Parameters
    ----------
    anchor_lat : float
        The anchor latitude.
    anchor_long : float
        The anchor longitude.
    nodes : list
        The list of node dictionaries.
    delta_type : str
        The type of delta ("ll" or "xy").

    Returns
    -------
    list[tuple[float, float]]
        The list of (lat, long) tuples.
    """
    pts = [(anchor_lat, anchor_long)]
    lat = anchor_lat
    long = anchor_long

    for n in nodes:
        delta_container = n.get("delta", {})
        if not delta_container:
            continue
        key = next(iter(delta_container.keys()))
        d = delta_container[key]

        if delta_type == "ll":
            dlat, dlong = ll_delta_to_deg(d)
            lat += dlat
            long += dlong
        elif delta_type == "xy":
            dx_m, dy_m = xy_delta_to_meters(d)
            lat, long = apply_xy_delta(lat, long, dx_m, dy_m)
        else:
            continue
        pts.append((lat, long))
    return pts

def plot_tim(all_paths, out_path) -> None:
    """
    Create a folium map with anchors and polylines for each region path.
    
    Parameters
    ----------
    all_paths : list
        A list of all paths to plot.
    out_path : str
        The output path for the generated map.
    """
    # Get center location for map
    all_coords = [pt for _, _, pts in all_paths for pt in pts]
    if not all_coords:
        raise SystemExit("No coordinates found to plot")
    avg_lat = sum(p[0] for p in all_coords) / len(all_coords)
    avg_lon = sum(p[1] for p in all_coords) / len(all_coords)

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=17, control_scale=True)

    for name, anchor, pts in all_paths:
        # Set Anchor
        folium.Marker(
            location=list(anchor),
            popup=f"{name}\n{anchor[0]:.7f}, {anchor[1]:.7f}",
            tooltip=f"{name}",
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(m)

        # Set Path
        if len(pts) >= 2:
            folium.PolyLine(pts, weight=4, opacity=0.9, tooltip=f"{name} path").add_to(m)

        # Set Nodes
        for i, (lat, lon) in enumerate(pts):
            folium.CircleMarker(
                location=[lat, lon],
                radius=3,
                fill=True,
                fill_opacity=0.9,
                popup=f"{name} p{i}: {lat:.7f}, {lon:.7f}",
            ).add_to(m)

    m.save(out_path)

def main():
    # Prompt user to select a JSON file
    json_path = select_json_file()
    if not json_path:
        print("No JSON file selected.")
        return

    # Build output filename
    prefix = os.path.splitext(os.path.basename(json_path))[0]
    output_html = f"{prefix}.html"

    data = json.loads(Path(json_path).read_text())

    all_paths = []
    for name, lat, long, nodes, delta_type in extract_regions(data):
        if delta_type is None:
            # No offsets; still drop an anchor
            pts = [(lat, long)]
            raise NotImplementedError("No offsets implemented.")
        else:
            pts = build_path_points(lat, long, nodes, delta_type)
        all_paths.append((name, (lat, long), pts))

    plot_tim(all_paths, output_html)
    print(f"Wrote {output_html}")

if __name__ == "__main__":
    main()
