import streamlit as st
import pandas as pd
import time
import folium
from streamlit_folium import folium_static
import heapq
import itertools
import requests

def load_data(file_path):
    data = pd.read_excel(file_path)

    # Filter out rows with non-string 'Route' values
    data = data[data['Route'].apply(lambda x: isinstance(x, str))]

    # Extract the locations
    locations = set()
    for route in data['Route']:
        loc1, loc2 = route.split(' - ')
        locations.add(loc1)
        locations.add(loc2)

    locations = list(locations)
    location_index = {loc: idx for idx, loc in enumerate(locations)}

    # Initialize the adjacency list for both distance and time
    adjacency_list_distance = {loc: [] for loc in locations}
    adjacency_list_time = {loc: [] for loc in locations}

    # Fill the adjacency lists with provided distances and times
    for _, row in data.iterrows():
        loc1, loc2 = row['Route'].split(' - ')
        dist = row['Distance']
        time = row['Time']
        route_category = row['Route_category']
        adjacency_list_distance[loc1].append((loc2, dist))
        adjacency_list_time[loc1].append((loc2, time))
        if route_category == 'two way':
            adjacency_list_distance[loc2].append((loc1, dist))
            adjacency_list_time[loc2].append((loc1, time))

    return locations, adjacency_list_distance, adjacency_list_time, location_index

def dijkstra(adjacency_list, start_vertex, end_vertex):
    pq = [(0, start_vertex, [])]
    seen = set()
    min_dist = {vertex: float('inf') for vertex in adjacency_list}
    min_dist[start_vertex] = 0

    while pq:
        (cost, current_vertex, path) = heapq.heappop(pq)
        if current_vertex in seen:
            continue
        seen.add(current_vertex)
        path = path + [current_vertex]

        if current_vertex == end_vertex:
            return path, cost

        for neighbor, weight in adjacency_list[current_vertex]:
            if neighbor not in seen:
                next_cost = cost + weight
                if next_cost < min_dist[neighbor]:
                    min_dist[neighbor] = next_cost
                    heapq.heappush(pq, (next_cost, neighbor, path))

    return [], float('inf')

def bellman_ford(adjacency_list, start_vertex, end_vertex):
    all_vertices = list(adjacency_list.keys())
    distance = {vertex: float('inf') for vertex in all_vertices}
    predecessor = {vertex: None for vertex in all_vertices}

    distance[start_vertex] = 0

    for _ in range(len(all_vertices) - 1):
        for vertex in all_vertices:
            for neighbor, weight in adjacency_list[vertex]:
                if distance[vertex] + weight < distance[neighbor]:
                    distance[neighbor] = distance[vertex] + weight
                    predecessor[neighbor] = vertex

    # Reconstruct path
    path = []
    current_vertex = end_vertex
    while current_vertex is not None:
        path.append(current_vertex)
        current_vertex = predecessor[current_vertex]
    path.reverse()

    return path, distance[end_vertex]

def get_route(start, end):
    url = f"http://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}?overview=full&geometries=geojson"
    response = requests.get(url)
    if response.status_code == 200:
        route = response.json()['routes'][0]['geometry']['coordinates']
        return [(coord[1], coord[0]) for coord in route]
    else:
        st.error(f"OSRM routing error: {response.status_code}")
        return []

def find_optimal_path(start_vertex, end_vertices, adjacency_list, algorithm='Dijkstra'):
    min_total_distance = float('inf')
    optimal_path = []

    for perm in itertools.permutations(end_vertices):
        path = [start_vertex]
        total_distance = 0

        for end_vertex in perm:
            if algorithm == 'Dijkstra':
                segment_path, segment_distance = dijkstra(adjacency_list, path[-1], end_vertex)
            elif algorithm == 'Bellman-Ford':
                segment_path, segment_distance = bellman_ford(adjacency_list, path[-1], end_vertex)
            else:
                raise ValueError("Unknown algorithm specified. Use 'Dijkstra' or 'Bellman-Ford'.")
            
            path.extend(segment_path[1:])
            total_distance += segment_distance

        if algorithm == 'Dijkstra':
            return_path, return_distance = dijkstra(adjacency_list, path[-1], start_vertex)
        elif algorithm == 'Bellman-Ford':
            return_path, return_distance = bellman_ford(adjacency_list, path[-1], start_vertex)
        
        path.extend(return_path[1:])
        total_distance += return_distance

        if total_distance < min_total_distance:
            min_total_distance = total_distance
            optimal_path = path

    return optimal_path, min_total_distance

def find_and_display_paths(locations, adjacency_list, lat_lon_data, start_vertex, end_vertices, algorithm):
    start_time = time.time()
    optimal_path, total_distance = find_optimal_path(start_vertex, end_vertices, adjacency_list, algorithm)
    end_time = time.time()
    runtime = end_time - start_time

    st.write(f"{algorithm} Algorithm Path:", optimal_path)
    st.write(f"{algorithm} Algorithm Total Distance:", total_distance)
    st.write(f"{algorithm} Algorithm Runtime: {runtime:.10f} seconds")

    if not optimal_path:
        st.error(f"{algorithm} algorithm did not find a path. Please check the input data and try again.")
    else:
        map_center = lat_lon_data[start_vertex]
        m = folium.Map(location=map_center, zoom_start=15)
        for loc in optimal_path:
            color = 'green' if loc == start_vertex else 'red' if loc in end_vertices else 'blue'
            folium.Marker(lat_lon_data[loc], popup=loc, icon=folium.Icon(color=color)).add_to(m)
        for i in range(len(optimal_path) - 1):
            loc1, loc2 = optimal_path[i], optimal_path[i + 1]
            start = lat_lon_data[loc1]
            end = lat_lon_data[loc2]
            route = get_route(start, end)
            if route:
                folium.PolyLine(route, color='blue' if algorithm == 'Dijkstra' else 'red').add_to(m)
        
        st.write(f"{algorithm} Algorithm Route:")
        folium_static(m)

# Streamlit app
st.title("Shortest Path using Dijkstra's Algorithm and Bellman-Ford Algorithm")

file_path = st.file_uploader("Upload the Excel file", type=["xlsx"])

if file_path:
    locations, adjacency_list_distance, adjacency_list_time, location_index = load_data(file_path)

    # Add latitude and longitude data
    lat_lon_data = {
        'Sukapura': (-6.967736652447319, 107.6357878929439),
        'Ciganitri': (-6.970417073652973, 107.63956764438949),
        'KU1': (-6.9743688142924345, 107.63162064549275),
        'TULT': (-6.969266317065273, 107.6281562512184),
        'Gapura': (-6.972527616350855, 107.63612266589308),
        'Kota': (-6.965761613527506, 107.63789558064254),
        'GKU': (-6.972911449954438, 107.62991322323856),
        'PBB': (-6.973869374267484, 107.63767978286768),
        'Gate_4': (-6.976103439208848, 107.6329211570838),
        'PGA': (-6.974807864750453, 107.6347274879698),
        'Gate_2': (-6.97324292330464, 107.63334620935919),
        'Gate_1': (-6.972157124210006, 107.63356826737754),
        'Bandung_technopark': (-6.971438829016563, 107.63142695221025),
        'Sukabirus': (-6.976544287227393, 107.63290971363602),
        'Sport_center': (-6.971573479922934, 107.62896914994343)
    }

    # Restrict start and end vertex options
    start_vertex_options = ['Sukabirus', 'Sukapura', 'Kota', 'Ciganitri', 'PBB']
    end_vertex_options = ['KU1', 'TULT', 'GKU']

    start_vertex = st.selectbox("Select Start Vertex", start_vertex_options)
    end_vertices = st.multiselect("Select End Vertices", end_vertex_options)

    optimization_criteria = st.radio("Optimize path based on:", ('Distance', 'Time'))
    algorithm = st.selectbox("Select Algorithm", ['Dijkstra', 'Bellman-Ford'])

    if st.button("Find Path"):
        if optimization_criteria == 'Distance':
            adjacency_list = adjacency_list_distance
        else:
            adjacency_list = adjacency_list_time
        find_and_display_paths(locations, adjacency_list, lat_lon_data, start_vertex, end_vertices, algorithm)
