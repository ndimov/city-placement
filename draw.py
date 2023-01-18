from collections import defaultdict
import osmnx as ox
import networkx as nx
from osmnx import utils_geo, simplification
import re
import matplotlib.colors as mc
import matplotlib.pyplot as plt
from data import presidents, states
from PIL import Image

from matplotlib.backend_bases import GraphicsContextBase, RendererBase
import matplotlib.pyplot as plt

import types

# hacks to make the line caps rounded
# https://stackoverflow.com/questions/11578760/matplotlib-control-capstyle-of-line-collection-large-number-of-lines
class GC(GraphicsContextBase):
    def __init__(self):
        super().__init__()
        self._capstyle = "round"


def custom_new_gc(self):
    return GC()


RendererBase.new_gc = types.MethodType(custom_new_gc, RendererBase)

# Per https://stackoverflow.com/a/74113918 this is a workaround for a bug in pyside
import matplotlib

matplotlib.use("tkagg")

# ----------------------------------------------------------------------

RED = "#e00000"
GREEN = "#26e026"
BLUE = "#4370cd"

# An old version of this puzzle used gradients within each color
# based on the value's position in the corresponding list
GRADIENTS = {
    "num": (RED, [str(i) for i in range(1, 100)]),
    "presidents": (GREEN, presidents),
    "states": (BLUE, states),
}
BASE_COLOR = "#444444"

LINE_STYLES = {BASE_COLOR: "solid", RED: "dashed", GREEN: "dashdot", BLUE: "dotted"}

matched_street_names = defaultdict(set)
radius = 500  # meters
cities = []
with open("cities.tsv") as f:
    for line in f:
        l = line.split("\t")
        cities.append(l)
cities = sorted(cities, key=lambda x: x[0])  # sort by city name

def gradient_color(name: str, street_name: str):
    """Return the color for the specified value in this gradient set, or None if this value isn't included"""

    base, values = GRADIENTS[name]
    for idx, match_value in enumerate(values):
        if name == "num":
            condition = match_value == street_name
        elif name == "presidents":
            condition = (
                any(match_value == keyword for keyword in street_name.split())
                and not "pierce elevated" in street_name  # houston
            )
        else:  # "states"
            condition = " " + match_value in " " + street_name
        if condition:
            matched_street_names[match_value].add(street_name)
            return base
    return None


def road_color(street_name):
    if street_name is None:
        return BASE_COLOR
    # OSM data allows multiple names on a single way
    if isinstance(street_name, list):
        street_name = " ".join(street_name)
    street_name = street_name.lower()
    keywords = street_name.split(" ")

    for keyword in keywords:
        nums = re.findall("\d+", keyword)
        # All the desired numbered streets have an ordinal suffix
        # There is a busway in LA labeled "10" or "I-10"
        if not any(keyword.endswith(suffix) for suffix in ["st", "nd", "rd", "th"]):
            continue
        # Fun fact: DC has a 13½th Street (on gmaps this is 13 1/2)
        if nums:
            number = nums[0]
            return gradient_color("num", number)
    for gradient in GRADIENTS:
        color = gradient_color(gradient, street_name)
        if color:
            return color
    return BASE_COLOR


def process_subgraph(subgraph):
    from osmnx import utils_graph

    if len(subgraph.edges()) == 0:
        return None
    # Remove duplicate edges (in either direction) so that
    # dashed lines are properly rendered
    subgraph = simplification.simplify_graph(subgraph)
    undirected = utils_graph.get_undirected(subgraph)
    return undirected


def plot_center(coords, filename):
    lat, long = coords
    roads = ox.graph_from_point(
        (lat, long),
        dist=radius,
        truncate_by_edge=True,
        # This was not included for the puzzle, but you probably want to
        # for example to keep the NJT in Jersey City's fire station pic
        retain_all=True,
        network_type="drive",
        simplify=False,  # see SW 1st becoming SW Washington in Portland
    )
    bbox = utils_geo.bbox_from_point((lat, long), radius)
    edges_with_colors = [
        ((u, v, k), road_color(data.get("name")))
        for u, v, k, data in roads.edges(keys=True, data=True)
    ]
    # Draw each distinct color as a separate subgraph
    subgraphs = [
        (
            process_subgraph(
                roads.edge_subgraph(
                    [
                        edge
                        for edge, color in edges_with_colors
                        if color == desired_color
                    ]
                )
            ),
            desired_color,
        )
        # most to least common
        for desired_color in [BASE_COLOR]
        + [GRADIENTS[name][0] for name in ["num", "presidents", "states"]]
    ]

    ax = None
    for subgraph, desired_color in subgraphs:
        if not subgraph:
            continue
        if len(subgraph.edges()) == 0:
            continue
        fig, ax = ox.plot_graph(
            subgraph,
            ax=ax,
            bbox=bbox,
            node_size=0,
            edge_color=desired_color,
            edge_linewidth=1.8,
            show=False,
            close=False,
            bgcolor="#fafafa",
            # NOTE: I hacked the library to pass in style keywords
            # such as this to the underlying gdf_edges.plot
            linestyle=LINE_STYLES[desired_color],
        )

    fig.set_frameon(False)
    full_filename = f"{filename}.png"
    fig.savefig(full_filename, dpi=300, bbox_inches="tight", pad_inches=0)

    img = Image.open(full_filename)
    img_w, img_h = img.size
    marker = Image.open("pin.png").convert("RGBA")
    old_marker_w, old_marker_h = marker.size
    marker = marker.resize((100, int(old_marker_h / old_marker_w * 100)))
    marker_w, marker_h = marker.size
    img.paste(
        marker,
        # Bottom middle of the marker should be exact center of image
        ((img_w - marker_w) // 2, img_h // 2 - marker_h),
        marker,  # For transparency
    )
    img.save(full_filename)
    plt.close()


def to_lat_long(center):
    # Splits string into floats (lat, long)
    return [float(i) for i in center.split(", ")]


for i, (city, fire_station_coord, city_hall_coord) in enumerate(cities):
    print(city)
    coords = list(map(to_lat_long, [city_hall_coord, fire_station_coord]))
    plot_center(coords[0], f"{i+1}a")
    plot_center(coords[1], f"{i+1}b")

print(matched_street_names)
