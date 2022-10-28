"""
A file containing some example code demonstrating how to turn .lss files into speedrun models
"""
from speedrun_models import BasicSpeedrunModel
from reset_strategies import get_strategy
from lss_reader import LSSReader, time_to_float


def main():
    # fix a split_step
    split_step = 0.1
    # construct an LSSReader object from a .lss file
    reader = LSSReader("ExampleData/CelesteAnyPForsakenCity.lss", use_igt=True)
    # extract segments
    min_date = "10/28/2022"
    segments = [
        reader.get_model_segment(0, split_step, compare_to="Personal Best", min_date=min_date),
        reader.get_model_segment(1, split_step, compare_to="Personal Best", min_date=min_date),
        reader.get_model_segment(2, split_step, compare_to="Personal Best", min_date=min_date),
    ]
    # specify the real time it takes to reset a run
    reset_time = 10
    # fix a goal time
    goal_split = reader.get_relative_split(time_to_float("1:40"), "Personal Best")
    # construct a model and calculate an optimal reset strategy from it
    model = BasicSpeedrunModel.from_segments(segments, goal_split, reset_time)
    strategy, record_density = get_strategy(model, print_progress=True)
    # print the results
    print(f"expected record time = {round(1/record_density/60, 1)} minutes")
    print("splits to reset at: " + " ".join(str(round(x, 1)) for x in strategy.reset_splits))


if __name__ == '__main__':
    main()
