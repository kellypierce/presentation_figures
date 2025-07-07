import pandas as pd
import matplotlib.pyplot as plt
import json
import math
import re
import numpy as np


def load_jsonl(fpath: str) -> pd.DataFrame:
    data: list[dict[str, str|int]] = []
    with open(fpath, "r") as f:
        for line in f:
            data.append(json.loads(line))
    data_df = pd.DataFrame.from_dict(data)
    bool_mapping = {"True": True, "False": False}
    try:
        data_df["include"] = [bool_mapping[i] for i in data_df["include"]]
    except KeyError:
        print("KeyError: 'include' field is improperly specified.")
        raise
    data_df = data_df[data_df['include'] == True]
    return data_df


def round_nearest(value: float|int, nearest: int, direction: str) -> float:
    if direction == "down":
        return math.floor(value/nearest) * nearest
    elif direction == "up":
        return math.ceil(value/nearest) * nearest
    else:
        raise ValueError("Direction must be 'down' or 'up'")


def aggregate_data(data: pd.DataFrame, years: int, vertical: bool, annotate_year: bool=False) -> pd.DataFrame:
    """Round event years down to nearest century and group events by their century of occurrence."""
    data['plot_date'] = [round_nearest(i, nearest=years, direction="down") for i in data['relative_year']]
    if annotate_year:
        data['event'] = [f"{row['event']} ({abs(row['relative_year'])})" for i, row in data.iterrows()]
    if vertical:
        data = data.sort_values(by=['relative_year'], ascending=False)
    else:
        data = data.sort_values(by=['relative_year'], ascending=True)
    plot_data = data.groupby('plot_date')['event'].agg(lambda x: '\n'.join(x)).reset_index()
    return plot_data


def calculate_text_height(data: pd.DataFrame, years_per_line) -> pd.DataFrame:

    # count number of text lines
    data['n_lines'] = [len(re.findall("\n", i)) for i in data['event']]
    data['text_height'] = data['n_lines'] * years_per_line

    # make all values positive and calculate bottom and top of text block
    offset = abs(min(0, min(data['plot_date'])))
    data['text_center'] = data['plot_date'] + offset
    data['text_top'] = data['text_center'] + (data['text_height'] / 2)
    data['text_bottom'] = abs(data['text_center']) - data['text_height']

    return data


def place_text_timeline(data: pd.DataFrame, overlap_buffer: float|int, vertical: bool = True) -> pd.DataFrame|None:

    # reshape and identify overlaps
    if vertical:
        data = data.sort_values(by="plot_date", ascending=False)  # most recent values at the top
    else:
        data = data.sort_values(by="plot_date", ascending=True)  # most recent values at the left
    data['overlap_buffer'] = (data['n_lines'] + 1) * overlap_buffer

    # does a record top overlap the bottom of the next record?
    data["overlaps_present"] = [False] + [True if data["text_top"].iloc[i] + data["overlap_buffer"].iloc[i] >= data["text_bottom"].iloc[i-1] else False for i in range(1, data.shape[0])]

    # bump everything down until there are no overlaps
    if data["overlaps_present"].any():
        overlap_data = data[data["overlaps_present"] == True]
        other_data = data[data["overlaps_present"] == False]
        for position in ["text_top", "text_center", "text_bottom"]:
            overlap_data[position] = overlap_data[position] - overlap_data["overlap_buffer"]
        data = pd.concat([overlap_data, other_data])
        return place_text_timeline(data, overlap_buffer=overlap_buffer)
    else:
        offset = abs(min(0, min(data['plot_date'])))
        for position in ["text_top", "text_center", "text_bottom"]:
            data[position] = data[position] - offset
        return data


def make_tick_marks(data: pd.DataFrame, interval_years: int) -> (list[int], list[str]):

    data_min = round_nearest(data["plot_date"].min(), interval_years, direction="down")
    data_max = round_nearest(data["plot_date"].max(), interval_years, direction="up")
    ticks = [i for i in range(data_min, data_max+interval_years, interval_years)]
    marks = [f"{abs(i)} BCE" if np.sign(i) == -1 else f"{i} AD" for i in ticks]

    return ticks, marks


def timeline_vertical(data: pd.DataFrame, years: int) -> None:

    fig, ax = plt.subplots(figsize=(7, 6))
    ax.set(title="")
    ax.hlines(data['plot_date'], 0, 0.1, color="k")
    ax.axvline(0, c="black", linewidth=10)
    ax.set_xlim(0, 1)

    # Annotate the lines and draw lines to annotations
    for i, event in data.iterrows():
        ax.plot([0.1, 0.2], [event['plot_date'], event['text_top']], color="black")
        text_position = event['text_center'] - years/2
        ax.annotate(
            event['event'],
            xy=(0.21, text_position),
            xytext=(0.21, text_position),
            bbox=dict(facecolor='white', alpha=0, edgecolor='none')
        )

    # update tick marks on y-axis
    ticks, marks = make_tick_marks(data, interval_years=years*5)
    plt.yticks(ticks, marks)

    # turn axis spines off; turn x-axis off
    for position in ['top', 'right', 'left', 'bottom']:
        ax.spines[position].set_visible(False)
    ax.xaxis.set_visible(False)

    plt.show()


def timeline_horizontal(data: pd.DataFrame) -> None:
    raise NotImplementedError


def main(data_fpath, years, vertical=True) -> None:

    # load files
    data = load_jsonl(data_fpath)

    # make the timeline
    data = aggregate_data(data, years=years)
    data = calculate_text_height(data, years_per_line=years)
    data = place_text_vertical_timeline(data, overlap_buffer=years)

    if vertical:
        timeline_vertical(data, years=years)
    else:
        timeline_horizontal(data)

if __name__ == "__main__":

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--data_fpath", required=True, help="Path to jsonl data file containing timeline data.")
    parser.add_argument("-v", "--vertical", action="store_true", default=True, help="If specified, create a vertical timeline.")
    parser.add_argument("-p", "--parameters", required=False, help="Additional parameters for timeline aesthetics.")
    parser.add_argument("-y", "--years", required=False, type=int, help="Number of years to aggregate", default=100)

    opts = parser.parse_args()
    if opts.parameters:
        raise NotImplementedError("Timeline aesthetics not yet implemented.")

    main(opts.data_fpath, opts.years, opts.vertical)
