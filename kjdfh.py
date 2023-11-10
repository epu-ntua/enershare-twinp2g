import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st

# Create a new graph
G = nx.DiGraph()

# Add nodes
G.add_node('Generator', pos=(0, 1))
G.add_node('Transmission Lines', pos=(1, 2))
G.add_node('Transformers', pos=(1, 0))
G.add_node('Distribution Lines', pos=(2, 1))
G.add_node('Loads', pos=(3, 1))

# Add edges
G.add_edge('Generator', 'Transmission Lines')
G.add_edge('Generator', 'Transformers')
G.add_edge('Transmission Lines', 'Distribution Lines')
G.add_edge('Transformers', 'Distribution Lines')
G.add_edge('Distribution Lines', 'Loads')

# Extract node positions
pos = nx.get_node_attributes(G, 'pos')

# Draw the graph
load_flow=nx.draw(G, pos, with_labels=True, node_size=3000, node_color='skyblue', font_size=10, font_weight='bold', arrowsize=20)
plt.title('Load Flow Diagram')
plt.show()

st.write(load_flow)
