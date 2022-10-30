"""
This file contains some code to verify that the other code still works. It is not commented at all so, it's just meant
for testing purposes.
"""
from speedrun_models import BasicSpeedrunModel, SplitDistribution
import random
from lss_reader import LSSReader, time_to_float
from reset_strategies import get_strategy, BasicStrategy


def sample_dist(dist: SplitDistribution):
    x = random.random()
    y = 0
    for i, p in enumerate(dist.probabilities):
        if x <= y + p:
            return dist.start_split + dist.split_step * i
        y += p
    return "reset"


def simulate_prob_of_record(model: BasicSpeedrunModel, iterations: int):
    n = 0
    for _ in range(iterations):
        split = 0
        for dist in model.segment_distributions:
            segment_time = sample_dist(dist)
            if segment_time == "reset":
                break
            split += segment_time
        else:
            if split <= model.goal_split+1e-6:
                n += 1
    return n/iterations


def simulate_record_density(strategy: BasicStrategy, max_time):
    model = strategy.model
    t = 0
    record_num = 0
    while t < max_time:
        s = 0
        for i, (segment_real_time, segment_dist) in enumerate(zip(model.real_times, model.segment_distributions)):
            t += segment_real_time
            segment_time = sample_dist(segment_dist)
            if segment_time == "reset":
                break
            s += segment_time
            if i != model.segment_num-1 and s >= strategy.reset_splits[i]-1e-6:
                break
        else:
            if s <= model.goal_split+1e-6:
                record_num += 1
    return record_num/t


def simulate_record_time(strategy: BasicStrategy, max_time: float):
    model = strategy.model
    total_t = 0
    n = 0
    sum_t = 0
    stop = False
    while True:
        t = 0
        while True:
            s = 0
            for i, (segment_real_time, segment_dist) in enumerate(zip(model.real_times, model.segment_distributions)):
                t += segment_real_time
                total_t += segment_real_time
                if total_t >= max_time:
                    stop = True
                    break
                segment_time = sample_dist(segment_dist)
                if segment_time == "reset":
                    break
                s += segment_time
                if i != model.segment_num - 1 and s >= strategy.reset_splits[i]-1e-6:
                    break
            else:
                if s <= model.goal_split + 1e-6:
                    break
            if stop:
                break
        if stop:
            break
        n += 1
        sum_t += t
    return sum_t/n


def verify_code_on_model(model: BasicSpeedrunModel, simulate_time: float, iterations: int):
    print("The following values should be almost the same")
    print(model.prob_of_record())
    print(simulate_prob_of_record(model, iterations))

    strategy, record_density = get_strategy(model, print_progress=False)
    print("The following values should be the same, (the last two only close enough to the first two)")
    print(1/record_density)
    print(1/strategy.compute_record_density())
    print(1/simulate_record_density(strategy, simulate_time))
    print(simulate_record_time(strategy, simulate_time))


def main():
    # test 1
    split_step = 0.1
    reader = LSSReader("ExampleData/CelesteAnyPForsakenCity.lss", use_igt=True)
    min_date = "10/28/2022"
    segments = [
        reader.get_model_segment(0, split_step, compare_to="Personal Best", min_date=min_date),
        reader.get_model_segment(1, split_step, compare_to="Personal Best", min_date=min_date),
        reader.get_model_segment(2, split_step, compare_to="Personal Best", min_date=min_date),
    ]
    reset_time = 10
    goal_split = reader.get_relative_split(time_to_float("1:40"), "Personal Best")
    model = BasicSpeedrunModel.from_segments(segments, goal_split, reset_time)
    verify_code_on_model(model, 50_000_000, 100_000)

    # test 2
    split_step = 0.05
    goal_split = -2
    reset_time = 10
    segments1 = [
        (30, SplitDistribution.from_gaussian(+1, 1, split_step, 5)),
        (120, SplitDistribution.from_gaussian(+1, 1, split_step, 5)),
        (120, SplitDistribution.from_gaussian(+1, 1, split_step, 5)),
        (30, SplitDistribution.from_gaussian(+1, 1, split_step, 5))
    ]
    model1 = BasicSpeedrunModel.from_segments(segments1, goal_split, reset_time)
    segments2 = segments1.copy()
    segments2[0] = (30, SplitDistribution.from_gaussian(-1, 1, split_step, 5, run_kill_prob=0.75))
    model2 = BasicSpeedrunModel.from_segments(segments2, goal_split, reset_time)
    verify_code_on_model(model1, 10_000_000, 100_000)
    verify_code_on_model(model2, 10_000_000, 100_000)


if __name__ == '__main__':
    main()
