import osmnx as ox
from osmnx import utils_geo
import re
import colorsys
import matplotlib.colors as mc
import matplotlib.pyplot as plt
from data import presidents, states


radius = 500  # meters
# centers = ["47.68199601897163, -122.35506428651688"]  # seattle fire station

cities = []
with open("cities.tsv") as f:
    for line in f:
        l = line.split("\t")
        cities.append(l)
cities = sorted(cities, key=lambda x: x[0])  # sort by city name

GRADIENTS = {
    "num": ("#ff0000", [str(i) for i in range(1, 100)]),  # TODO: make logarithmic?
    "presidents": ("#00ff00", presidents),
    "states": ("#0000ff", states),
}
PLACEHOLDER = "#999999"


def gradient_color(name: str, street_name: str):
    """Return the color for the specified value in this gradient set, or None if this value isn't included"""

    base, values = GRADIENTS[name]
    for idx, match_value in enumerate(values):
        condition = (
            match_value == street_name if name == "num" else match_value in street_name
        )
        if condition:
            clr = colorsys.rgb_to_hsv(*mc.to_rgb(base))
            return colorsys.hsv_to_rgb(
                clr[0], clr[1] * (1 - (idx / len(values))), clr[2]
            )  # the end white value is considered just outside the list
    return None


def road_color(name):
    if name is None:
        return PLACEHOLDER
    name = "".join(name).lower()
    keywords = name.split(" ")

    for keyword in keywords:
        nums = re.findall("\d+", keyword)
        if nums:
            number = nums[0]
            return gradient_color("num", number)
    for gradient in GRADIENTS:
        color = gradient_color(gradient, name)
        if color:
            return color
    return PLACEHOLDER


def plot_center(center, filename):
    lat, long = [float(i) for i in center.split(", ")]
    roads = ox.graph_from_point(
        (lat, long), dist=radius, truncate_by_edge=True, network_type="drive"
    )
    bbox = utils_geo.bbox_from_point((lat, long), radius)
    ec = [road_color(data.get("name")) for u, v, data in roads.edges(data=True)]
    fig, ax = ox.plot_graph(
        roads,
        bbox=bbox,
        node_size=0,
        edge_color=ec,
        show=False,
        close=False,
        bgcolor="#00000000",
    )
    # fig, ax = ox.plot_figure_ground(
    #     roads,
    #     node_size=0,
    #     edge_color=ec,
    #     dist=radius,
    #     show=False,
    #     close=False,
    #     bgcolor="#000000ff",
    # )
    ax.scatter(long, lat, c="#dd0000")
    # plt.Circle((long, lat), radius, color="#aaaaaa", fill=False)
    plt.savefig(filename)


for i, (city, stn_coord, city_hall_coord) in enumerate(cities):
    print(city)
    # TODO: strip out relevant coords or whatever
    plot_center(stn_coord, f"{i+1}a.svg")
    plot_center(city_hall_coord, f"{i+1}b.svg")
