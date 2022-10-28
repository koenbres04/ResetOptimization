"""
A python file containing classes and methods for reading .lss files
"""
from speedrun_models import SplitDistribution
from xml.etree import ElementTree
import numpy as np
from typing import Tuple


class LSSReadingException(Exception):
    """
    An exception object related to reading an .lss file.
    """
    pass


# a function for converting time strings like "00:10:11.2" to a float number of seconds
def time_to_float(string: str):
    sign = 1
    if string.startswith("-"):
        sign = -1
        string = string[1:]
    time_bits = [float(x) for x in string.split(":")]
    if len(time_bits) == 3:
        return sign*(3600*time_bits[0]+60*time_bits[1]+time_bits[2])
    elif len(time_bits) == 2:
        return sign*(60*time_bits[0]+time_bits[1])
    raise LSSReadingException("Too many :'s in a time")


# a function for converting (american) day and time strings like "10/26/2022 17:53:03" and "10/26/2022" to an integer
# for comparisons. This integer is NOT guaranteed to be the the number of seconds since 0/0/0 00:00:00
def day_and_time_to_int(string: str):
    if " " in string:
        day_str, time_str = string.split(" ")
        time_bits = [int(x) for x in time_str.split(":")]
        time = sum(x*y for x, y in zip((3600, 60, 1), time_bits))
    else:
        day_str = string
        time = 0
    day_bits = [int(x) for x in day_str.split("/")]
    day_time = 24*3600*(day_bits[1]+31*(day_bits[0]+12*day_bits[2]))
    return day_time+time


def read_time_element(element, use_igt: bool):
    time_elt = element.find("GameTime" if use_igt else "RealTime")
    if time_elt is not None:
        return time_to_float(time_elt.text)
    return None


class LSSReader:
    """
    A class for reading .lss (Livesplit splits) files.
    """
    def __init__(self, file_name: str, use_igt: bool, encoding="utf-8-sig"):
        """"
        Construct an LSSReader from a file.
        """
        # for some reason Livesplit exports it's files with a weird encoding so specifying the encoding is necessary
        with open(file_name, "r", encoding=encoding) as file:
            file_contents = file.read()
        # create an Element object from the xml string
        root = ElementTree.fromstring(file_contents)
        # fetch the list of attempts with their id's and the times that they where performed
        self.attempts = dict()
        for attempt in root.find("AttemptHistory"):
            self.attempts[attempt.attrib["id"]] = (day_and_time_to_int(attempt.attrib["started"]), [], [])
        # extract the offset
        self.offset = time_to_float(root.find("Offset").text)
        if self.offset != 0:
            raise LSSReadingException("Currently reading .lss files with a start time is not supported :(.")
        # extract the segments data
        segments = root.find("Segments")
        self.segment_names = []
        best_segments = []
        comparison_splits = dict()
        for segment in segments:
            # extract the name of the segment
            self.segment_names.append(segment.find("Name").text)
            # extract the best time for this segment
            best_segments.append(read_time_element(segment.find("BestSegmentTime"), use_igt=use_igt))
            # extract comparison splits
            for split_time in segment.find("SplitTimes"):
                name = split_time.attrib["name"]
                if name not in comparison_splits.keys():
                    comparison_splits[name] = []
                comparison_splits[name].append(read_time_element(split_time, use_igt))
            # read the in game time and real time of each attempt for this segment
            for time_element in segment.find("SegmentHistory"):
                attempt_id = time_element.attrib["id"]
                segment_time = read_time_element(time_element, use_igt=use_igt)
                segment_real_time = read_time_element(time_element, use_igt=False)
                if segment_time is not None:
                    self.attempts[attempt_id][1].append(segment_time)
                if segment_real_time is not None:
                    self.attempts[attempt_id][2].append(segment_real_time)
        # store the comparison segment times
        self.comparison_segments = {"Best Segments": best_segments}
        for name, splits in comparison_splits.items():
            splits = [0.] + splits
            segment_times = []
            for i in range(1, len(splits)):
                if splits[i] is None:
                    segment_times.append(None)
                else:
                    segment_times.append(splits[i]-splits[i-1])
            self.comparison_segments[name] = segment_times

    def get_relative_split(self, time, compare_to, segment_index=-1):
        segment_times = self.comparison_segments[compare_to]
        for segment_time in segment_times[:(segment_index % len(segment_times))+1]:
            time -= segment_time
        return time

    def get_segment_data(self, segment, min_date=None, max_date=None, compare_to=None,
                         resets_as_run_kill=False) -> list:
        """
        Get a list of the segment times of segment 'segment' for all attempts between min_date and max_date.
         - segment: an index or a name specifying the segment
         - min_date, max_date: strings like "10/9/2022", "10/9/2022 10:15" and "10/9/2022 10:15:30"
         - compare_to: specifies what to save the segment times relative to. It can be:
            * a float giving the segment time to compare to
            * equal to "Best Segments" specifying that we should compare to the best segments according to LiveSplit
            * any other string that is the name of splits from the .lss file
         - When resets_as_run_kill is set to true, a reset during this segment will be counted as a run kill.
          This does not work well when you reset for other reasons, like being on a bad pace.
          Setting this setting to true is best when doing practice runs.
        """
        # compare the string dates to integers for easier comparisons
        min_date_int = np.NINF if min_date is None else day_and_time_to_int(min_date)
        max_date_int = np.PINF if max_date is None else day_and_time_to_int(max_date)
        # find the index of the specified segment
        if isinstance(segment, int):
            if segment >= len(self.segment_names):
                raise LSSReadingException(f"Invalid segment index {segment}.")
            segment_num = segment
        else:
            if segment not in self.segment_names:
                raise LSSReadingException(f"No segment named '{segment}' found.")
            segment_num = self.segment_names.index(segment)
        # find what we want to compare the splits to based on the 'compare_to' parameter
        if compare_to is None:
            compare_time = 0
        elif isinstance(compare_to, float) or isinstance(compare_to, int):
            compare_time = compare_to
        elif isinstance(compare_to, str):
            if compare_to not in self.comparison_segments.keys():
                raise LSSReadingException(f"No splits named '{compare_to}' found to compare to.")
            compare_time = self.comparison_segments[compare_to][segment_num]
            if compare_time is None:
                raise LSSReadingException(f"The comparison splits '{compare_to}' does not have the right time "
                                          f"type (igt vs real time).")
        else:
            raise ValueError("The value given for compare_to is not None, a number or a string.")
        # loop through all attempts between min_date and max_date and extract the times from it
        data = []
        for date_int, real_times, segment_times in self.attempts.values():
            if min_date_int <= date_int <= max_date_int and len(segment_times) >= segment_num+1:
                data.append(segment_times[segment_num]-compare_time)
            if resets_as_run_kill and len(segment_times) == segment_num:
                data.append("run kill")
        return data

    def average_real_time_length(self, segment, min_date=None, max_date=None) -> float:
        """
        Get the average real time length of segment 'segment' for all attempts between min_date and max_date.
        - segment: an index or a name specifying the segment
        - min_date, max_date: strings like "10/9/2022", "10/9/2022 10:15" and "10/9/2022 10:15:30"
        """
        # compare the string dates to integers for easier comparisons
        min_date_int = np.NINF if min_date is None else day_and_time_to_int(min_date)
        max_date_int = np.PINF if max_date is None else day_and_time_to_int(max_date)
        # find the index of the segment with segment_name as name
        # find the index of the specified segment
        if isinstance(segment, int):
            if segment >= len(self.segment_names):
                raise LSSReadingException(f"Invalid segment index {segment}.")
            segment_num = segment
        else:
            if segment not in self.segment_names:
                raise LSSReadingException(f"No segment named '{segment}' found.")
            segment_num = self.segment_names.index(segment)
        # loop through all attempts between min_date and max_date and extract the real time from it
        n = 0
        total_time = 0.
        for date_int, real_times, segment_times in self.attempts.values():
            if min_date_int <= date_int <= max_date_int and len(real_times) >= segment_num+1:
                total_time += real_times[segment_num]
                n += 1
        return total_time/n

    def get_model_segment(self, segment, split_step, min_date=None, max_date=None, compare_to=None,
                          run_kill_threshold=np.PINF, time_clamp=(np.NINF, np.PINF)) -> Tuple[float, SplitDistribution]:
        """
        Get a list of the segment times of segment 'segment' for all attempts between min_date and max_date.
         - segment: an index or a name specifying the segment
         - split_step: the precision to which time is made discrete
         - min_date, max_date: strings like "10/9/2022", "10/9/2022 10:15" and "10/9/2022 10:15:30"
         - compare_to: specifies what to save the segment times relative to. It can be:
            * a float giving the segment time to compare to
            * equal to "Best Segments" specifying that we should compare to the best segments according to LiveSplit
            * any other string that is the name of splits from the .lss file
         - When resets_as_run_kill is set to true, a reset during this segment will be counted as a run kill.
           This does not work well when you reset for other reasons, like being on a bad pace.
           Setting this setting to true is best when analysing practice runs.
         - time_clamp: any times outside of this range are discarded
        """
        real_time = self.average_real_time_length(segment, min_date, max_date)
        segment_data = self.get_segment_data(segment, min_date, max_date, compare_to)
        return real_time, SplitDistribution.from_data(segment_data, split_step, run_kill_threshold, time_clamp)
