from collections import defaultdict
from numpy import full
import osmnx as ox
from osmnx import utils_geo
import re
import colorsys
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
        # self._joinstyle = "round"


def custom_new_gc(self):
    return GC()


RendererBase.new_gc = types.MethodType(custom_new_gc, RendererBase)

# ----------------------------------------------------------------------


kws = defaultdict(set)

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
    "presidents": ("#26e026", presidents),
    "states": ("#4370cd", states),
}
PLACEHOLDER = "#444444"


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
            # and all(
            #     match_piece in street_name.split()
            #     for match_piece in match_value.split()
            # )
        if condition:
            kws[match_value].add(street_name)
            # print("MATCH:", match_value, "STREET NAME:", street_name, "BASE:", base)
            return base
            # clr = colorsys.rgb_to_hsv(*mc.to_rgb(base))
            # return colorsys.hsv_to_rgb(
            #     clr[0], clr[1] * (1 - (idx / len(values))), clr[2]
            # )  # the end white value is considered just outside the list
    return None


def road_color(name):
    if name is None:
        return PLACEHOLDER
    if isinstance(name, list):
        name = " ".join(name)
    name = name.lower()
    keywords = name.split(" ")

    for keyword in keywords:
        nums = re.findall("\d+", keyword)
        # remove a busway in LA
        # if keyword == "10" or keyword == "i-10":
        if not any(keyword.endswith(suffix) for suffix in ["st", "th", "rd"]):
            continue
        # fun fact, DC has a 13½ street (on gmaps this is 13 1/2)
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
        (lat, long),
        dist=radius,
        truncate_by_edge=True,
        network_type="drive",
        simplify=False,  # see SW 1st becoming SW Washington in Portland
    )
    bbox = utils_geo.bbox_from_point((lat, long), radius)
    edges_with_colors = [
        ((u, v, k), road_color(data.get("name")))
        for u, v, k, data in roads.edges(keys=True, data=True)
    ]
    subgraphs = [
        (
            roads.edge_subgraph(
                [edge for edge, clr in edges_with_colors if clr == desired_clr]
            ),
            desired_clr,
        )
        # most to least common
        for desired_clr in [PLACEHOLDER]
        + [GRADIENTS[name][0] for name in ["num", "presidents", "states"]]
    ]
    # edge_zorder = []
    # for val in ec:
    #     zorder = 10
    #     if val == GRADIENTS["num"][0]:
    #         zorder = 20
    #     elif val == GRADIENTS["presidents"][0]:
    #         zorder = 30
    #     elif val == GRADIENTS["states"][0]:
    #         zorder = 40
    #     edge_zorder.append(zorder)
    ax = None
    for subgraph, desired_clr in subgraphs:
        if len(subgraph.edges()) == 0:
            continue
        fig, ax = ox.plot_graph(
            subgraph,
            ax=ax,
            bbox=bbox,
            node_size=0,
            edge_color=desired_clr,
            edge_linewidth=1.8,
            # edge_zorder=edge_zorder,
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
    # ax.scatter(long, lat, c="#dd0000")
    # remove the padding
    # ax.get_xaxis().set_visible(True)
    # ax.get_yaxis().set_visible(True)
    # plt.Circle((long, lat), radius, color="#aaaaaa", fill=False)
    # line_collection = ax.get_children()[0]
    # for line in line_collection.lines:
    #     print(line)

    fig.set_frameon(False)
    full_filename = f"{filename}.png"
    fig.savefig(full_filename, dpi=300, bbox_inches="tight", pad_inches=0)

    img = Image.open(full_filename)
    img_w, img_h = img.size
    marker = Image.open("pin-jacqui-b.png").convert("RGBA")
    old_marker_w, old_marker_h = marker.size
    marker = marker.resize((100, int(old_marker_h / old_marker_w * 100)))
    marker_w, marker_h = marker.size
    img.paste(
        # btm mid of marker is exact center of img
        marker,
        ((img_w - marker_w) // 2, img_h // 2 - marker_h),
        marker,  # for transparency
    )
    img.save(full_filename)
    plt.close()


def to_lat_long(center):
    # Splits string into floats (lat, long)
    return [float(i) for i in center.split(", ")]


for i, (city, stn_coord, city_hall_coord) in enumerate(cities):
    print(city)
    # TODO: strip out relevant coords or whatever
    # doesn't seem too necessary. honestly props to them if they can do it,
    # seems more fun than the actual id part
    coords = list(map(to_lat_long, [city_hall_coord, stn_coord]))
    # coords = sorted(
    #     [to_lat_long(coord) for coord in [stn_coord, city_hall_coord]],
    #     key=lambda x: x[1],
    # )
    plot_center(coords[0], f"{i+1}a")
    plot_center(coords[1], f"{i+1}b")

print(kws)
