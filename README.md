# Workflow


## Overview

Workflow is a utility for configuring and automating
your Python-based experiments. Workflow sets up an
experiment like a flowchart, then runs the experiment
step by step. It can also keep track of experiment data,
organize output files, and record the experiment progress
for you. You implement each type of step as a Python
class, then Workflow can run your step's procedure whenever
it encounters that type of step in an experiment's
flowchart. Your Python code can access convenient helper
methods provided by Workflow, such as get_config() to
help you read configuration values without having to
manually parse a config file yourself.


## Why Should I Use This?

Workflow was designed to improve researcher productivity.
It is common for researchers to have an existing set of
Python scripts, that each do some task, such as setting
up a simulation. However, the configuration and running
of these individual scripts tends to be a laborious and
error-prone manual process. If you find this aspect of
your work difficult, distracting, or annoying then you
should try using this library. Here are some benefits:

- Structure your experiments intuitively and flexibly
as flowcharts.

- Incrementally automate your lab's computing tasks,
based on your needs and priorities.

- Maintain focus on science rather than script setup.

- Manage experiments without having to always write
code; enable non-programmers and new people in your lab
to modify existing experiments or create entirely new
experiments by themselves.

- Visualize the state of your experiments, making it
quick to understand and communicate what is happening.

- Precisely record your experiments, including all steps
and data involved. This allows for accurate manual review
or automated analysis of how an experiment was run.

- Rerun or continue old experiments with one command. This
lets you or your peer reviewers reproduce an experiment
effortlessly.

- Incorporate your existing code into Workflow with
minimal changes and no lock-in. Load configuration and
experiment data from Workflow, call your function with
that data, then store results data to Workflow. Done!

- Easily share experiment data among different parts of
the experiment, with the researcher running the experiment,
with automated tools monitoring the experiment, and when
retracing the experiment.

- Write new Python code once then re-use it for different
experiments.

- Access configuration parsing, state management, and other
utilities without having to implement them all yourself.

- Share experiments, common tasks, and types of steps with your
colleagues to reduce duplication of effort.


## Conceptual Details

Below is a description of the main concepts you need to understand
in order to use this library effectively. You should also
refamiliarize yourself with what a flowchart represents:

https://en.wikipedia.org/wiki/Flowchart


### Config File

A TOML config file must be specified when running the Workflow
command script `workflow.py <config_file.toml>`. An example
config file is provided:

config_files/examples/demo/demo_config.toml

A config file defines the parameters of the overall
experiment, the initial experiment state, and the specific
steps and decisions involved in the experiment. In the
config file, you specify the name and type of each part
of the experiment, as well as any configuration information
that type of part needs. You can also specify
'first_part' and 'next_part' information, if you want to
automate your experiment, either partially or fully.


### Output Files

The out_dir you specify in the config file tells Workflow
where you like to save the results of running experiments,
in general or for a particular project. When you run
Workflow it will create a subdirectory in the out_dir with
your experiment's name, then another subdirectory in that
with the run number for the experiment. For example, if
you specify an outdir of /home/username/my_project/my_results
and the experiment name is experiment_a and it is the 
first time running that experiment, Workflow will save files
to /home/username/my_project/my_results/experiment_a/run_1.
Workflow determines the run number based on the highest number
run in the experiment directory. If a relative path is provided
it will be treated as relative to the directory that contains
the config file.


#### Trace File

A JSON trace file is output by Workflow such that a run of an 
experiment can be recorded and reproduced. The trace
records all steps performed by Workflow, state changes,
decisions, and custom events. The trace allows software tools
and humans to monitor the progress of an ongoing experiment
or analyze a previous run. Data is streamed to the file while
the experiment is running, so it can be watched with the "tail -f"
command on Linux or be consumed by visualization tools in real
time. You can rerun or continue an old experiment using its
trace file, and Workflow will try to retrace the path that was taken.


### Experiment Data

Workflow's ExperimentManager will maintain experiment variables
in a data dictionary as name-value pairs. Different parts of
the experiment can read and write the experiment data, allowing them
to share state with each other or with the researcher. Any type of
data can be stored, but consider making the data serializable
to JSON if you want it to be recorded correctly in the trace
file. Basic Python types, like str or dict, and small sets of
data are best. For example, it is better to store a file
path str rather than a file handle object in the dictionary.
Data is global for the whole experiment but consider using dot and
underscore notations in your data names to represent nested and
internal data, respectively (e.g. my_part._private_data). A
missing data is represented by None so that should be checked for,
along with the type, as needed. It is important to use the API in
experiment_parts.py for reading inputs and writing outputs
so as to maintain a coherent state and record all data changes
to the trace file.

Note: it is important to understand that 'config values' and
'experiment data' are two different things. The config values
do not change while an experiment is running and instead explain
how to setup the parts of the experiment before it is run.
Experiment data, on the other hand, is the state of the running
experiment that changes as steps are run and output data.


### Experiment Parts

Workflow's ExperimentManager conducts an experiment
as a sequence of steps, charting a path through a 'flowchart'.
Each part of the experiment needs a unique name identifier. Use
dot notation to refer to nested parts (e.g. flow_1.step_1).
Each type of part needs to be implemented as a Python class
with certain required methods filled in. See experiment_parts.py
for more information. You should take a look at the provided
demo_config.toml file for an example of how to define the
different parts of an experiment. There are just three kinds
of entities in a flowchart: steps, decisions, and flows.

A 'step' is usually a single computing task. It is typically
represented as a small box shape in a flowchart. Almost all of
your Python code should be implemented as steps. Each type
of step is defined as a class that inherits from Step
(see experiment_parts.py). Steps are intended as re-usable
'building blocks' and should do just one meaningful unit of
work. Each step has a 'config_values' table with name-value pairs,
which is used when setting up the step. Each type of step will have
different configuration values. Each step can be configured
with 'input_names' and 'output_names' tables, each mapping the
names of data in the manager's data dictionary to the argument
names the step implementation expects. Using these name mappings
prevents name collisions and gives researchers the freedom to
name their experiment data the way they want. Each step can also
optionally specify the 'next_part' name of what to run
automatically after the step is finished. If missing, the
researcher is asked to specify the name of the part to run next.

A 'decision' is usually a single decision point, that
determines what step to do next in the experiment, among
multiple diffferent choices. It is typically represented as
a 'diamond' shape in a flowchart. Each type of decision is
defined as a class that inherits from Decision. Decisions
are intended as simple branches, like if-else statements
in the workflow, defining the different routes that can be
taken through the experiment. Each decision can be configured with
'config_values' and 'input_names' tables. However, unlike a step,
a decision has no 'output_names' table. This is because
only steps should be changing data. Decisions should only be
reading config values and data values for deciding what to
do next and should never be modifying data as a side effect.
Each decision should specify a 'next_part' table (not just a name),
mapping a part identifier to the route names the decision
implementation expects. You should generally avoid creating
your own decision types, and instead use the decision types provided
by the library, such as the ConditionalDecision type, paired
with a step that prepares the data before the decision is made.

A 'flow' is a grouping of steps, decisions, and other flows. It
is typically represented as a large rectangular container with
a dotted line border in a flowchart. Each type of flow is
defined as a class that inherits from Flow. Flows can be used
to represent common sections of experiments. Flows can also give
special behavior to their contained steps. For example, the 'load'
flow copies all the parts from another config file before running
them. You should generally avoid creating your own flow types,
and instead use the flow types provided by the library, such as
the LoadFlow type, and grouping related steps inside that flow.

If the manager encounters a situation where the 'next' part
of the experiment is None or invalid, or if a step/decision
crashes with an uncaught exception, it will prompt the
researcher to specify the part of the experiment to go next,
leave the current flow, or end the entire experiment.


### Visualization

An accompanying 'view experiment' tool is provided, which
shows an ongoing or complete experiment in a web page. The
tool watches the trace file of an experiment and renders the
structure of the experiment as a flowchart, lists the
experiment data, and provides the current state of the
experiment run as new trace events occur. This tool is
useful for visualizing the current or previous states of
the experiment. You MUST install some dependencies to use
this tool (see view_experiment.py for details). After the
proper setup, you can view an experiment in two ways. If
you want to run the viewer in a standalone way, to view an
old experiment run for example, then run the view_experiment.py
script. If you want to start a new experiment run with the
viewer running alongside Workflow, pass the '--view' parameter
to the workflow.py script.


## Including the Library in Your Code

If you want to add Workflow to your lab's Git repo, you should
add it as a Git submodule. Basically, this will include the
library as a special directory inside your repo, but Git will
still track the library as a separate, nested repo. This lets
you avoid copy+paste errors, and you can bring in new versions
of the library at your discretion using 'git pull' or similar
commands. It also makes it so Git version controls which commit
you are looking at in the library repo. The command to setup the
submodule will be like this (tweak as needed):

`git submodule add https://github.com/kenneth-tucker/workflow workflow`

The command should be run from the directory you want the
submodule to appear in, probably the root of your repo.

Then you'll want to define your own part_types.py file. Copy
the one provided in the library repo and modify the import
paths as needed. Then add any new parts you implement into
the part_types dictionary. Your config files will need to
specify the relative or absolute path to your part_types.py
file.

NEVER make changes in the workflow submodule. All of your
lab's code and config files should be stored in your repo,
NOT in the library submodule. This is for a few reasons. First,
you don't want your proprietary code in the open source library.
Second, you don't want to lose your changes when someone pulls
in updates for the library. Thirdly, the Workflow library
developer wishes to keep his repo general purpose, so any lab
can use freely use it.

If you find a bug or want to suggest a new feature, please submit
a ticket here:

https://github.com/kenneth-tucker/workflow/issues

Be sure to include a meaningful title, complete description (with
examples), and clearly identify if it is a bug report or a feature
request. PLEASE be patient, the author only supports this library
in his spare time. You may fork the repo, if you wish to modify it
yourself. Make sure to keep the LICENSE file in tact.


### Creating New Types of Parts

When adding a new step, decision, or flow be sure to put
the class name in the 'part_types' dictionary in your part_types.py.
It's best to look at existing types of parts for guidance on how
to implement your own type of part.


## Credits

I love you Matt! I hope this library assists you and your
colleagues in discovering nature's secrets and improving
people's lives!
