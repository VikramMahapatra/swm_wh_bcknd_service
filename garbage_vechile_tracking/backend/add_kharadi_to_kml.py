#!/usr/bin/env python3
"""
Add Kharadi ward boundaries from GeoJSON to ward-boundaries.kml
"""

import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Load the Kharadi GeoJSON
geojson_path = r'c:\Users\vikik\Downloads\export.geojson'
kml_path = r'c:\Users\vikik\Projects\PyProjects\Zentrixel\garbage\garbage_vechile_tracking\public\ward-boundaries.kml'

print("Loading Kharadi GeoJSON...")
with open(geojson_path, 'r', encoding='utf-8') as f:
    geojson = json.load(f)

# Extract the boundary polygon coordinates from GeoJSON
print("Extracting Kharadi boundaries...")
all_coords = []
for feature in geojson['features']:
    if feature['geometry']['type'] == 'LineString':
        for coord in feature['geometry']['coordinates']:
            all_coords.append(coord)

# Create boundary from the coordinates
# Format for KML: lng,lat,elevation (spaces between coordinates)
kml_coords = ' '.join([f"{lng},{lat},0" for lng, lat in all_coords])

# Load existing KML
print("Loading existing KML...")
tree = ET.parse(kml_path)
root = tree.getroot()

# Define KML namespace
ns = {'kml': 'http://www.opengis.net/kml/2.2'}

# Create new Placemark for Kharadi
placemark = ET.Element('Placemark')

# Add name
name = ET.SubElement(placemark, 'name')
name.text = 'Kharadi'

# Add ExtendedData with SimpleData fields
extended_data = ET.SubElement(placemark, 'ExtendedData')

# Add ward name
ward_data = ET.SubElement(extended_data, 'SimpleData', {'name': 'ward'})
ward_data.text = 'Kharadi'

# Add prabhag
prabhag_data = ET.SubElement(extended_data, 'SimpleData', {'name': 'prabhag'})
prabhag_data.text = 'Kharadi Ward'

# Add Geometry - MultiGeometry with outer boundary
multi_geom = ET.SubElement(placemark, 'MultiGeometry')
poly = ET.SubElement(multi_geom, 'Polygon')

# Outer boundary
outer_boundary = ET.SubElement(poly, 'outerBoundaryIs')
linear_ring = ET.SubElement(outer_boundary, 'LinearRing')
coordinates = ET.SubElement(linear_ring, 'coordinates')
coordinates.text = kml_coords

# Find the Document element and add placemark
document = root.find('.//kml:Document', ns) or root.find('.//Document')
if document is not None:
    document.append(placemark)
    print("Kharadi placemark added to Document")
else:
    # If no Document, add to root
    root.append(placemark)
    print("Kharadi placemark added to root")

# Pretty print and save
def prettify(elem):
    """Return a pretty-printed XML string."""
    rough_string = ET.tostring(elem, 'utf-8')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")

# Save the updated KML
print("Saving updated KML...")
with open(kml_path, 'w', encoding='utf-8') as f:
    # Write XML declaration
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    # Get the root without XML declaration from prettify
    xml_str = prettify(root)
    # Remove the XML declaration from prettify
    lines = xml_str.split('\n')[1:]  # Skip the declaration
    f.write('\n'.join(lines))

print(f"\n✅ Successfully added Kharadi boundaries to KML!")
print(f"   Total coordinates: {len(all_coords)}")
print(f"   KML file: {kml_path}")
