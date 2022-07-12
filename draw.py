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
    "num": ("#e00000", [str(i) for i in range(1, 100)]),
    "presidents": ("#00ff00", presidents),
    "states": ("#26e026", states),
}
PLACEHOLDER = "#444444"


def gradient_color(name: str, street_name: str):
    """Return the color for the specified value in this gradient set, or None if this value isn't included"""

    base, values = GRADIENTS[name]
    for idx, match_value in enumerate(values):
        condition = (
            match_value == street_name if name == "num" else match_value in street_name
        )
        if condition:
            return base
            # clr = colorsys.rgb_to_hsv(*mc.to_rgb(base))
            # return colorsys.hsv_to_rgb(
            #     clr[0], clr[1] * (1 - (idx / len(values))), clr[2]
            # )  # the end white value is considered just outside the list
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


def plot_center(coords, filename):
    lat, long = coords
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
        edge_linewidth=1.8,
        show=False,
        close=False,
        bgcolor="#fafafa",
        # bgcolor="#00000000",  # transparent
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
    # remove the padding
    # ax.get_xaxis().set_visible(True)
    # ax.get_yaxis().set_visible(True)
    # plt.Circle((long, lat), radius, color="#aaaaaa", fill=False)

    fig.set_frameon(False)
    fig.savefig(f"{filename}.png", dpi=300, bbox_inches="tight", pad_inches=0)
    plt.close()


def to_lat_long(center):
    # Splits string into floats (lat, long)
    return [float(i) for i in center.split(", ")]


for i, (city, stn_coord, city_hall_coord) in enumerate(cities):
    print(city)
    # TODO: strip out relevant coords or whatever
    coords = sorted(
        [to_lat_long(coord) for coord in [stn_coord, city_hall_coord]],
        key=lambda x: x[1],
    )
    plot_center(coords[0], f"{i+1}a")
    plot_center(coords[1], f"{i+1}b")
    exit()
