# Speedrun Reset Optimization

This project implements an algorithm for optimising reset strategies in speedrunning.
This is not only usefull for determining when to reset during a run, but also it allows you to quantitatively judge when to go for a risky strategy or for a more safe one.

## The basic idea

Before we can describe the algorithm we need to establish how exactly we model speedrunning.

### A speedrun model

First we split the run up into a fixed number of *segments*.
Associated to a segment are two different types of time.
We have *real time*, the time spent in real life performing a run.
And we have *in game time*, the time in the game that you wish to minimize.
If you are halfway through a run, the sum of the in game duration of the previous segments is called your current *split*.
Often these splits are measured relative to a different run so that these numbers are smaller.

For simplicity we assume that each segment takes some fixed amount of real time.
This is a pretty good approximation for optimized runs as then the real time spent during a run doesn't vary much compared to the full run length.
This approximation cannot be made for the in game time duration.

For each segment we give a probability distribution for the in game time that the segment takes, called the *segment distribution*.
In order to not have our measly finite computers to not explode we discretize time to some fixed precision (in the code this is called the `split_step`).
Finally we have a *goal split*: A split at the end of the run that we want to go below.
This is (somewhat crudely) visualized in the image below.

![A visualization of a speedrun model.](model_drawing.png "A visualization of a speedrun model.")

All of this data together forms a *speedrun model*.
The class `BasicSpeedrunModel` stores all of this data.

### Record density
A *reset strategy* is a sequence splits, one for the end of each segment, where you reset at the end of a segment if your current split is higher than the one in the sequence.
Our goal is to find an optimal reset strategy, but what do we mean by optimal?
The goal of speedrunning is to reach a goal split as fast as possible, so we need to minimize the expected amount of real time it takes to reach the goal time.
Actually it will be easier to think of 1 divided by this quantity: the *record density*.
Loosly speaking, the record density is the amount of records per unit real time of an infinite chain of runs.



### The algorithm

...


I intend on explaining this algorithm and why it works in more mathematical rigour in a LaTeX document.

## Example applications

The obvious application is to use the optimal reset strategy during a run.
The calculated expected record time could be used to estimate how long it will take to obtain a record, however this might have some unwanted psychologial effects.
A much more interesting application is the comparison of strategies and routes.

Another example is Cannonless in the Super Mario 64 16 start category.
Cannonless is a strategy to the 'Blast Away the Wall' star in Whomp's Fortress without using the cannon.
This strategy saved around 30 seconds over using the cannon at the cost of only working about 20% of the time.
This meant that a lot of runs where reset at this point in the run.
Then Sockfolder found a setup for this trick that made the strategy 100% consistent at the cost of about 10 seconds.
(This was later lowerd to 6 seconds)
Despite the time loss the consistency made the strategy worth it.
However when the record went lower and lower timesaves where harder to find.
As a result runners started using the original inconsistent strategy again.
(See [this](https://www.youtube.com/watch?v=R_wscUcbynk) video by Summoning Salt.)
How do we make this exact?
When is a fast risky strategy better than a slow consistent strategy?
By making a speedrun model for each strategy we can compare the record densities for different goal splits.
We see that for higher goal times the consistent strategy gives a lower optimal record density than, but for lower goal times the risky strategy gives the best record density.
This is illustrated in the `example2` method of `example_code.py`.



## Getting started

At the moment this project consists of just python code and cannot really be compiled in any way.
All the python code is contained in the PyCharm project ResetOptimizationCode.
The full algorithm is contained in the files `speedrun_models.py` and `reset_strategies.py`.
Example code is provded in `example_code.py`.
Only the numpy library is needed to run the code.

The hardest thing about modelling a speedrun is finding the segment distributions.
For this you can create empirical distributions based on data using the `SplitDistribution.from_data` method.
It would be ideal if this data could be automatically gathered by a timer like LiveSplit, but unfortunately I (the owner of this repository) could not understand how to write a LiveSplit component.


## Room for improvement
- Models are only models.
The definition of a speedrun model can be improved in many ways while still keeping an algorithm for finding an optimal strategy relatively easy.
For example at the end of a segment we could allow the runner to not only decide whether or not to reset, but also to decide which strategy to employ during the next segment.
This would require giving a segment distribution for each strategy.
Another example would be to allow additional variables (like the number of ammo the runner has at the end of a segment) to be taken into account when deciding wether or not to reset. 
- At the moment generating segment distributions is quite hard.
Making a livesplit extension for automatically saving splits to a file would be a huge help.
If you feel like contributing feel free to email me (the owner of this repository).