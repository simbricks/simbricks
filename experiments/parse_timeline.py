import sys
import numpy as np
import matplotlib.pyplot as plt


def parse_timeline(file_name):
    timeline = np.load(file_name)

    # more to be added
    plot_execution_ratio(timeline, file_name + '_ratio.png')


def plot_execution_ratio(timeline, plot_name, num_intervals=100):
    durations = timeline[1:] - timeline[:-1]
    time_interval = (timeline[-1] - timeline[0]) / num_intervals
    time_offset, flag = 0, -2
    # span[0], span[1]: sum of idle time, sum of execution time
    span, ratio_list = [0, 0], []
    for duration in durations:
        while time_offset + duration > time_interval:
            remaining = time_interval - time_offset
            span[flag] = span[flag] + remaining
            duration = duration - remaining
            time_offset = 0
            ratio_list.append(span[1] / sum(span))
            span = [0, 0]
        else:
            time_offset = time_offset + duration
            span[flag] = span[flag] + duration
            flag = ~flag
    fig = plt.figure()
    plt.plot(ratio_list)
    plt.xlabel("time intervals")
    plt.ylabel("ratio of execution (non-blocking)")
    fig.savefig(plot_name)
    return ratio_list


if __name__ == "__main__":
    if len(sys.argv) == 2:
        parse_timeline(sys.argv[1])
    else:
        print("usage: python parse_timeline.py log_file")
