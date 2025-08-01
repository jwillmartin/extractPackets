#!/usr/bin/env python3
import pandas as pd
import folium
import os
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
        title="Select BSM Payload CSV",
        filetypes=[("CSV files", "*.csv")]
    )
    return csv_path

def main():
    # Prompt user to select a CSV file
    csv_path = select_csv_file()
    if not csv_path:
        print("No CSV file selected.")
        return

    # Build output filename
    prefix = os.path.splitext(os.path.basename(csv_path))[0]
    output_html = f"{prefix}.html"

    # Read data
    df = pd.read_csv(csv_path)
    if 'latitude' not in df.columns or 'longitude' not in df.columns:
        raise ValueError('CSV must contain "latitude" and "longitude" columns')

    # Compute the center of the map
    center_lat = df['latitude'].mean()
    center_lon = df['longitude'].mean()

    # Create a folium map
    map = folium.Map(location=[center_lat, center_lon], zoom_start=14)

    # Plot each point
    for lat, lon in zip(df['latitude'], df['longitude']):
        folium.CircleMarker(
            location=[lat, lon],
            radius=3,
            fill=True,
            fill_opacity=0.7
        ).add_to(map)

    # Save and report
    map.save(output_html)
    print(f"Map saved to {output_html}")

if __name__ == '__main__':
    main()
