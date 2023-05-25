import pypsa
import numpy as np

network = pypsa.Network()
n_buses = 3

for i in range(n_buses):
    network.add("Bus", "My bus {}".format(i), v_nom=20.0)


for i in range(n_buses):
    network.add(
        "Line",
        "My line {}".format(i),
        bus0="My bus {}".format(i),
        bus1="My bus {}".format((i + 1) % n_buses),
        x=0.1,
        r=0.01,
    )

network.add("Generator", "My gen", bus="My bus 0", p_set=100, control="PQ")

network.generators
network.generators.p_set
network.add("Load", "My load", bus="My bus 1", p_set=100)

network.loads

network.loads.p_set

network.loads.q_set = 100.0
network.pf()
network.lines_t.p0
network.buses_t.v_ang * 180 / np.pi
network.buses_t.v_mag_pu


