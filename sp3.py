import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd

# Load the provided Excel file
file_path = 'datashortest.xlsx'
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

# Initialize the distance matrix with infinities
num_locations = len(locations)
distance_matrix = [[float('inf')] * num_locations for _ in range(num_locations)]

# Fill the distance matrix with provided distances
for _, row in data.iterrows():
    loc1, loc2 = row['Route'].split(' - ')
    dist = row['Distance']
    route_category = row['Route_category']
    idx1, idx2 = location_index[loc1], location_index[loc2]
    distance_matrix[idx1][idx2] = dist
    if route_category == 'two way':
        distance_matrix[idx2][idx1] = dist

# Replace infinities with 0 for diagonal elements (not required for the graph)
for i in range(num_locations):
    distance_matrix[i][i] = 0

# Define the start and end vertices for the shortest path
start_vertex = 'Ciganitri'
end_vertex = 'KU1'

# Create the directed graph
G = nx.DiGraph()

# Add nodes
for loc in locations:
    G.add_node(loc)

# Add edges with distances
for i in range(num_locations):
    for j in range(num_locations):
        if i != j and distance_matrix[i][j] != float('inf'):
            G.add_edge(locations[i], locations[j], weight=distance_matrix[i][j])

# Compute the shortest path using Dijkstra's algorithm
shortest_path = nx.dijkstra_path(G, source=start_vertex, target=end_vertex)
shortest_path_length = nx.dijkstra_path_length(G, source=start_vertex, target=end_vertex)

print("Shortest Path:", shortest_path)
print("Shortest Path Length:", shortest_path_length)

# Get positions for all nodes
pos = nx.spring_layout(G)

# Plot the graph
plt.figure(figsize=(12, 8))
nx.draw(G, pos, with_labels=True, node_color='lightblue', node_size=2000, font_size=10, font_weight='bold')

# Add edge labels, excluding self-loops
edge_labels = {(locations[i], locations[j]): distance_matrix[i][j] for i in range(num_locations) for j in range(num_locations) if i != j and distance_matrix[i][j] != float('inf')}
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_color='black')

# Highlight the shortest path
path_edges = [(shortest_path[i], shortest_path[i + 1]) for i in range(len(shortest_path) - 1)]
nx.draw_networkx_edges(G, pos, edgelist=path_edges, edge_color='r', width=2)

# Show the plot
plt.title(f"Shortest Path from {start_vertex} to {end_vertex} with Distances")
plt.show()
