"""
A python file containing classes and methods speedrun models.
"""
import dataclasses
import numpy as np
from typing import List
from math import ceil, exp, floor


@dataclasses.dataclass
class SplitDistribution:
    """
    A class for storing discrete in game time distributions.
     - start_split and split_step: describe how time is discretized.
       i.e. the possible times are [start_split, start_split+split_step, start_split+2*split_step, ...]
     - probabilities: a numpy array of floats where the i'th entry gives the probability of
       the segment taking start_split+i*split_step in game time. Note that these probabilities need not add up to 1. The
       difference with 1 gives the probability of the run being killed.
    """
    start_split: float
    split_step: float
    probabilities: np.ndarray

    # gives the length of the probabilities array
    @property
    def length(self) -> int:
        return len(self.probabilities)

    # returns the probability of a dead run
    def get_run_kill_prob(self) -> float:
        return 1-np.sum(self.probabilities)

    # computes the in game time distribution of performing two segments after each other
    def convolve(self, other):
        assert self.split_step == other.split_step
        return SplitDistribution(self.start_split + other.start_split, self.split_step,
                                 np.convolve(self.probabilities, other.probabilities))

    # creates a SplitDistribution with a normal distribution
    @classmethod
    def from_gaussian(cls, mu, sigma, split_step, radius, run_kill_prob=0):
        k = ceil(radius / split_step)
        length = 2 * k + 1
        probabilities = np.zeros(length, dtype=float)
        for i in range(length):
            probabilities[i] = exp(-1 / 2 * ((i - k) * split_step / sigma) ** 2)
        return cls(mu - k * split_step, split_step, probabilities / np.sum(probabilities) * (1 - run_kill_prob))

    # creates a SplitDistribution from a list of data points that are either numbers or the string "run kill"
    @classmethod
    def from_data(cls, data_points, split_step, run_kill_threshold=np.PINF, clamp_range=(np.NINF, np.PINF)):
        data_points = [x for x in data_points if isinstance(x, str) or clamp_range[0] <= x <= clamp_range[1]]
        run_kill_points = sum(1 for x in data_points if isinstance(x, str) or x >= run_kill_threshold)
        discrete_points = [round(x/split_step) for x in data_points
                           if (not isinstance(x, str)) and x < run_kill_threshold]
        start_index = min(discrete_points)
        probabilities = np.zeros(max(discrete_points)-start_index+1, dtype=float)
        probability_unit = 1/(len(discrete_points)+run_kill_points)
        for i in discrete_points:
            probabilities[i-start_index] += probability_unit
        return cls(start_index*split_step, split_step, probabilities)

    # return a copy of this distribution object
    def copy(self):
        return SplitDistribution(self.start_split, self.split_step, self.probabilities.copy())


class BasicSpeedrunModel:
    """
    A model of a speedrun where the only choice per segment is whether or not to reset.
     - segment_num: number of segments
     - split_step: the precision to which in game time is discretized
     - segment_distributions: a list of SplitDistributions, one for each segment
     - goal_split: the goal in game time to reach (<=)
     - real_times: a list giving the real time length of each segment
    """

    def __init__(self, segment_num: int, split_step: float, real_times,
                 segment_distributions: List[SplitDistribution], goal_split: float):
        self.segment_num = segment_num
        self.split_step = split_step
        self.segment_distributions = segment_distributions
        self.goal_split = goal_split
        self.real_times = real_times

        self.split_range_lengths = [1]
        for dist in segment_distributions:
            self.split_range_lengths.append(dist.length + self.split_range_lengths[-1] - 1)
        self.start_splits = [0]
        for dist in segment_distributions:
            self.start_splits.append(self.start_splits[-1] + dist.start_split)

    # creates a speedrun model from a list of tuples consisting tuples describing a segment of the run.
    # Each tuple consists of the real time length of the segment together with a SplitDistribution object describing
    # it's length
    @classmethod
    def from_segments(cls, segments: List, goal_split, reset_time=0):
        real_times = [t for t, d in segments]
        real_times[0] += reset_time
        distributions = [d for t, d in segments]
        return BasicSpeedrunModel(len(segments), segments[0][1].split_step, real_times, distributions, goal_split)

    # gives the discretised version of self.goal_split
    @property
    def goal_index(self):
        return floor((self.goal_split - self.start_splits[-1]) / self.split_step)

    # computes the probability of a run reaching the goal split without resets
    def prob_of_record(self):
        # deal with the edge case that reaching the goal split is impossible
        if self.goal_index < 0:
            return 0
        # obtain a distribution for the total run time using the convolve method
        distribution = self.segment_distributions[0].copy()
        for dist in self.segment_distributions[1:]:
            distribution = distribution.convolve(dist)
        # calculate what the probability of a record
        return np.sum(distribution.probabilities[0:self.goal_index+1])
