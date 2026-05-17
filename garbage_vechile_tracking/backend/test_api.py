import requests
import json

try:
    # Test routes API
    response = requests.get('http://localhost:8000/api/routes/')
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        routes = response.json()
        print(f"\nTotal routes: {len(routes)}")
        
        if routes:
            first_route = routes[0]
            print(f"\nFirst route: {first_route['name']}")
            print(f"Route ID: {first_route['id']}")
            print(f"Pickup points: {len(first_route.get('pickup_points', []))}")
            
            if first_route.get('pickup_points'):
                print("\nFirst pickup point:")
                pp = first_route['pickup_points'][0]
                print(f"  Name: {pp['name']}")
                print(f"  Lat: {pp['latitude']}, Lng: {pp['longitude']}")
    else:
        print(f"Error: {response.text}")

except Exception as e:
    print(f"Error: {e}")
