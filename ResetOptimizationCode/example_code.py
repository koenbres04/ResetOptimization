"""
A file containing some example code demonstrating how to use speedrun_models.py and reset_strategies.py
"""
from speedrun_models import BasicSpeedrunModel, SplitDistribution
from reset_strategies import get_strategy


def example_1():
    # In this example code we demonstrate how risky strategies are better early into a run than later into a run
    # first we fix how we discretise time
    split_step = 0.01

    # now we construct the first example model with no risky strats
    goal_split = -2  # the goal in game time relative to some run, like a pb
    reset_time = 10  # the time it takes to start a new run
    segments1 = [
        (30, SplitDistribution.from_gaussian(+1, 1, split_step, 5)),
        (120, SplitDistribution.from_gaussian(+1, 1, split_step, 5)),
        (120, SplitDistribution.from_gaussian(+1, 1, split_step, 5)),
        (30, SplitDistribution.from_gaussian(+1, 1, split_step, 5))
    ]
    model1 = BasicSpeedrunModel.from_segments(segments1, goal_split, reset_time)

    # now we modify this model to make the first segment more risky
    segments2 = segments1.copy()
    segments2[0] = (30, SplitDistribution.from_gaussian(-1, 1, split_step, 5, run_kill_prob=0.75))
    model2 = BasicSpeedrunModel.from_segments(segments2, goal_split, reset_time)

    # now we modify this model to make the first segment more risky
    segments3 = segments1.copy()
    segments3[-1] = (30, SplitDistribution.from_gaussian(-1, 1, split_step, 5, run_kill_prob=0.75))
    model3 = BasicSpeedrunModel.from_segments(segments3, goal_split, reset_time)

    # now we calculate the record densities of these models with the optimal reset strategies
    strategy_1, record_density_1 = get_strategy(model1)
    print(f"expected record time without any risky strategy: {round(1 / record_density_1)}")
    print("splits to reset at:",  " ".join(str(round(x, 2)) for x in strategy_1.reset_splits))
    strategy_2, record_density_2 = get_strategy(model2)
    print(f"expected record time with a risky strategy early in the run: {round(1 / record_density_2)}")
    print("splits to reset at:",  " ".join(str(round(x, 2)) for x in strategy_2.reset_splits))
    strategy_3, record_density_3 = get_strategy(model3)
    print(f"expected record time with a risky strategy late in the run: {round(1 / record_density_3)}")
    print("splits to reset at:",  " ".join(str(round(x, 2)) for x in strategy_3.reset_splits))


def example_2():
    # In this example we demonstrate how lowering the goal time can make risky strategies better than safe ones

    # first we give some parameters that we keep the same throughout the example models
    split_step = 0.01  # how much is time discretized
    reset_time = 10  # the time it takes to start a new run

    # now we construct two lists of segments, one with a safer strategy in the 3rd segment than the other
    safe_segments = [
        (30, SplitDistribution.from_gaussian(+1, 1, split_step, 5)),
        (120, SplitDistribution.from_gaussian(+1, 1, split_step, 5)),
        (120, SplitDistribution.from_gaussian(+1, 1, split_step, 5)),
        (30, SplitDistribution.from_gaussian(+1, 1, split_step, 5))
    ]
    risky_segments = safe_segments.copy()
    risky_segments[2] = (120, SplitDistribution.from_gaussian(-1, 1, split_step, 5, run_kill_prob=0.9))

    # construct models using these segments and two different goal splits
    goal_split_1 = -1
    model1 = BasicSpeedrunModel.from_segments(safe_segments, goal_split_1, reset_time)
    model2 = BasicSpeedrunModel.from_segments(risky_segments, goal_split_1, reset_time)
    goal_split_2 = -2
    model3 = BasicSpeedrunModel.from_segments(safe_segments, goal_split_2, reset_time)
    model4 = BasicSpeedrunModel.from_segments(risky_segments, goal_split_2, reset_time)

    # now we calculate the optimal reset strategies and their
    strategy_1, record_density_1 = get_strategy(model1)
    print(f"expected record time with a safe strategy and goal split {goal_split_1}: {round(1 / record_density_1)}")
    print("splits to reset at:",  " ".join(str(round(x, 2)) for x in strategy_1.reset_splits))
    strategy_2, record_density_2 = get_strategy(model2)
    print(f"expected record time with a risky strategy and goal split {goal_split_1}: {round(1 / record_density_2)}")
    print("splits to reset at:",  " ".join(str(round(x, 2)) for x in strategy_2.reset_splits))
    strategy_3, record_density_3 = get_strategy(model3)
    print(f"expected record time with a safe strategy and goal split {goal_split_2}: {round(1 / record_density_3)}")
    print("splits to reset at:",  " ".join(str(round(x, 2)) for x in strategy_3.reset_splits))
    strategy_4, record_density_4 = get_strategy(model4)
    print(f"expected record time with a risky strategy and goal split {goal_split_2}: {round(1 / record_density_4)}")
    print("splits to reset at:",  " ".join(str(round(x, 2)) for x in strategy_4.reset_splits))

    # this gives the following output:
    #   expected record time with a safe strategy and goal split -1: 17179
    #   splits to reset at: 0.0 0.44 0.93
    #   expected record time with a risky strategy and goal split -1: 22570
    #   splits to reset at: 0.33 1.28 1.01
    #   expected record time with a safe strategy and goal split -2: 66245
    #   splits to reset at: -0.14 0.09 0.33
    #   expected record time with a risky strategy and goal split -2: 55074
    #   splits to reset at: 0.16 0.85 0.28
    # we see that when our goal split is higher, the safe strategy is preferable, but when our goal split is lower
    # the risky strategy is preferable


if __name__ == '__main__':
    example_1()
    print(" ")
    example_2()
