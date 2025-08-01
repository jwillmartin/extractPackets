#!/usr/bin/env python3
import os
import pandas as pd
import folium
import tkinter as tk
from tkinter import filedialog

def select_csv_file():
    """
    Open a file dialog to select a CSV file.

    Returns
    -------
    csv_path : str
        Path to the selected CSV file or an empty string if cancelled.
    """
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    csv_path = filedialog.askopenfilename(
        title="Select SDSM Payload CSV",
        filetypes=[("CSV files", "*.csv")]
    )
    return csv_path

def get_unique_coordinates(csv_path):
    """
    Read the CSV and return unique latitude/longitude pairs.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file containing latitude and longitude columns.

    Returns
    -------
    unique_pts : pd.DataFrame
        DataFrame with unique latitude and longitude pairs.
    """
    # Read the lat/long columns
    df = pd.read_csv(csv_path, usecols=["lat", "long"], index_col=False)

    # Coerce to numbers and drop invalid
    df["lat"]  = pd.to_numeric(df["lat"],  errors="coerce")
    df["long"] = pd.to_numeric(df["long"], errors="coerce")
    unique_pts = (
        df.dropna(subset=["lat", "long"])
          .drop_duplicates(subset=["lat", "long"])
    )
    return unique_pts

def plot_sdsms(unique_pts):
    """
    Create a folium map with unique latitude/longitude points.

    Parameters
    ----------
    unique_pts : pd.DataFrame
        DataFrame with unique latitude and longitude pairs.

    Returns
    -------
    map : folium.Map
        A folium map object with markers for each unique point.
    """
    # Initialize map at first unique point
    first = unique_pts.iloc[0]
    map = folium.Map(
        location=[float(first["lat"]), float(first["long"])],
        zoom_start=14
    )

    # Add one marker per unique point
    for _, row in unique_pts.iterrows():
        folium.Marker(
            location=[float(row["lat"]), float(row["long"])],
            popup=f"lat: {row['lat']:.6f}\nlong: {row['long']:.6f}"
        ).add_to(map)

    # Fit the map so all points are visible
    sw = [float(unique_pts["lat"].min()),  float(unique_pts["long"].min())]
    ne = [float(unique_pts["lat"].max()),  float(unique_pts["long"].max())]
    map.fit_bounds([sw, ne])

    return map

def main():
    # Prompt user to select a CSV file
    csv_path = select_csv_file()
    if not csv_path:
        print("No CSV file selected.")
        return

    # Build output filename
    prefix = os.path.splitext(os.path.basename(csv_path))[0]
    output_html = f"{prefix}.html"

    # Get unique coordinates from the CSV
    unique_pts = get_unique_coordinates(csv_path)
    if unique_pts.empty:
        print("No valid latitude/longitude pairs found.")
        return
    count = len(unique_pts)
    print(f"Found {count} unique coordinate(s).")

    # Plot the map
    map = plot_sdsms(unique_pts)

    # Save and report
    map.save(output_html)
    print(f"Map of unique coordinates saved to: {output_html}")

if __name__ == "__main__":
    main()
