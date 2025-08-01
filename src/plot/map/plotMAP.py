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
        title="Select MAP Payload CSV",
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

    # Load and deduplicate
    df = pd.read_csv(csv_path)
    unique = df.drop_duplicates(subset=["intersectionID"])[
        ["intersectionID", "latitude", "longitude"]
    ]

    # Center map
    center_lat = unique["latitude"].mean()
    center_lon = unique["longitude"].mean()
    map = folium.Map(location=[center_lat, center_lon], zoom_start=13)

    # Add markers
    for _, row in unique.iterrows():
        folium.Marker(
            location=[row["latitude"], row["longitude"]],
            popup=f"ID: {int(row['intersectionID'])}",
            icon=folium.Icon(icon="road", prefix="fa")
        ).add_to(map)

    # Save and report
    map.save(output_html)
    print(f"Map saved to {output_html}")

if __name__ == "__main__":
    main()
