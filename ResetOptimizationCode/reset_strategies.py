"""
A python file containing classes and methods for generating reset strategies.
"""
from speedrun_models import BasicSpeedrunModel
from math import ceil
import numpy as np
import dataclasses
from typing import Tuple


@dataclasses.dataclass
class BasicStrategy:
    """
    A basic reset strategy.
     - model: the model for which strategy this is a strategy
     - reset_indices: an array of integers describing above (>=) what splits to reset
    """
    model: BasicSpeedrunModel
    reset_indices: np.ndarray

    # create a BasicStrategy object from splits above which you reset
    @classmethod
    def from_reset_splits(cls, model: BasicSpeedrunModel, reset_splits):
        return BasicStrategy(model, np.array([ceil((s - a) / model.split_step)
                                              for a, s in zip(model.start_splits[1:], reset_splits)], dtype=int))

    # get the splits above to reset from a BasicStrategy object
    @property
    def reset_splits(self):
        return [s + self.model.split_step * i for i, s in zip(self.reset_indices, self.model.start_splits[1:-1])]

    # compute the record density of this strategy
    def compute_record_density(self):
        # initialise the distribution of splits
        distribution = self.model.segment_distributions[0].copy()
        t = self.model.real_times[0]
        expected_time = distribution.get_run_kill_prob()*t
        for i, reset_index in enumerate(self.reset_indices):
            # calculate the probability of resetting at the end of this segment and update the split distribution to
            # take this resetting into account
            if reset_index < 0:
                reset_prob = np.sum(distribution.probabilities)
                distribution.probabilities[:] = 0
            else:
                reset_prob = np.sum(distribution[reset_index:])
                distribution.probabilities[reset_index:] = 0
            # update the expected time with this
            expected_time += reset_prob * t
            # update the expected time based on the probability of the run being killed during the next segment
            expected_time += (np.sum(distribution.probabilities) *
                              self.model.segment_distributions[i + 1].get_run_kill_prob() *
                              (t+self.model.real_times[i + 1]))
            # update the distribution for the next segment
            distribution = distribution.convolve(self.model.segment_distributions[i + 1])
            t += self.model.real_times[i + 1]
        # calculate the probabilities of failing at the final segment or reaching the goal split
        fail_prob = 0
        record_prob = 0
        goal_index = self.model.goal_index
        for j in range(0, distribution.length):
            if j <= goal_index:
                record_prob += distribution.probabilities[j]
            else:
                fail_prob += distribution.probabilities[j]
        expected_time += (fail_prob + record_prob) * t
        return record_prob / expected_time


def update_strategy(model: BasicSpeedrunModel, possible_record_density, prob_of_record_out=None) \
        -> Tuple[np.array, float]:
    """
    Compute the reset_indices of a strategy for model of higher record density than possible_record_density
    (assuming that it is possible to achieve possible_record_density).
     - prob_of_record_out: an optional list which to add the intermediate probability of record arrays
    output: a list of reset indices and the record density of this strategy
    """
    # initiate the output array of reset indices
    reset_indices = np.zeros(model.segment_num, dtype=int)
    # initiate the expected time that the remaining segments will take for each split
    expected_time = np.zeros(model.split_range_lengths[-1], dtype=float)
    # initiate the probability of getting a record in this run for each split
    prob_of_record = np.zeros(model.split_range_lengths[-1], dtype=float)
    if model.goal_index >= 0:
        prob_of_record[0:model.goal_index+1] = 1
    # optionally save the prob_of_record_list
    if prob_of_record_out is not None:
        prob_of_record_out.append(prob_of_record)
    # now we loop through all the segments from the last to the first
    for i in range(model.segment_num - 1, -1, -1):
        # for each possible split before this segment we calculate the expected time that the rest of the run will take
        # and the probability that the rest of this run will result in a record
        segment_distribution = model.segment_distributions[i]
        new_expected_time = np.convolve(segment_distribution.probabilities[::-1], expected_time, "valid")
        new_expected_time += model.real_times[i]
        new_prob_of_record = np.convolve(segment_distribution.probabilities[::-1], prob_of_record, "valid")
        # use this to compute the record density of the remaining segments if the run is not reset
        continue_record_density = new_prob_of_record / new_expected_time
        # do some binary search to find the smallest split index b where resetting gives a worse record density
        if continue_record_density[0] < possible_record_density:
            b = 0
        elif continue_record_density[-1] >= possible_record_density:
            b = len(continue_record_density)
        else:
            a = 0
            b = len(continue_record_density) - 1
            while b - a > 1:
                c = (b - a) // 2 + a
                if continue_record_density[c] < possible_record_density:
                    b = c
                else:
                    a = c
        reset_indices[i] = b
        # update the new_expected_time and new_prob_of_record arrays based on the reset index found
        if b >= 0:
            new_expected_time[b:] = 0
            new_prob_of_record[b:] = 0
        else:
            new_expected_time[:] = 0
            new_prob_of_record[:] = 0
        expected_time = new_expected_time
        prob_of_record = new_prob_of_record
        # optionally save the prob_of_record_list
        if prob_of_record_out is not None:
            prob_of_record_out.append(prob_of_record)
    # check if the new strategy actually improved the record density
    if reset_indices[0] != 1:
        raise ValueError("The record density given could not be achieved!")
    return reset_indices[1:], prob_of_record[0] / expected_time[0]


def get_strategy(model: BasicSpeedrunModel, *, max_iterations: int = 100,
                 print_progress=False, return_record_probabilities=False):
    """
    Computes the optimal reset strategy of a speedrun model.
    Returns an optimal BasicStrategy object, its record density and optionally its list of record probability arrays
    """
    # compute a lower bound for the optimal record density using a strategy of completing every run
    record_density = model.prob_of_record() / sum(model.real_times)
    # stop early if getting a record is impossible
    if record_density == 0:
        if print_progress:
            print("Getting a record is impossible!")
        return BasicStrategy(model, np.array(model.split_range_lengths[1:])), 0

    last_reset_indices = None
    prob_of_record_out = None
    for i in range(max_iterations):
        # calculate a strategy of higher record density than 'record_density' and update record_density accordingly
        if return_record_probabilities:
            prob_of_record_out = []
        new_reset_indices, record_density = update_strategy(model, record_density, prob_of_record_out)
        # terminate the process when no better strategy can be found
        if last_reset_indices is not None and (last_reset_indices == new_reset_indices).all():
            last_reset_indices = new_reset_indices
            if print_progress:
                print(f"Process terminated after {i + 1} iterations!")
            break
        last_reset_indices = new_reset_indices
        if print_progress:
            print(f"* after {i + 1} iterations:")
            print(f"   - {new_reset_indices} or {BasicStrategy(model, new_reset_indices).reset_splits}")
            print(f"   - {1/record_density = }")

    # return the results
    if return_record_probabilities:
        return BasicStrategy(model, last_reset_indices), record_density, prob_of_record_out
    else:
        return BasicStrategy(model, last_reset_indices), record_density
