# Workflow

## Overview

Workflow is a utility for configuring and managing
simulation experiments. Workflow sets up an experiment
using a config file, then runs the experiment as
a series of steps and decision points. It organizes
all output files for you and records the experiment
progress in a trace file, for later review or rerun.


## Config File

Defines the parameters of the overall experiment,
initial experiment state, and the specific steps and
decisions involved in the experiment.

A config file is specified when running the Workflow
utility command `workflow.py <config_file.toml>`. An
example config file config_files/examples/demo/demo_config.toml
is provided. The TOML format is recommended because it
is simple yet versatile, similar the INI format but
expanded. See  https://toml.io/en/v1.0.0 for more info
about the TOML format.


## Output Files

The tree structure of the output files is hierarchical.

TODO clean up this description

The first level for an experiment typically contains
directories for each of the primary analyses produced by
cpptraj. For example, control_1/, control_2/, control_3/,
test_1/, test_2/, test_3/ would be present for an
experiment with a control and a test condition and 3
replicate simulations. Within each of these directories is
the PDB file output of cpptraj along with directories for
each of the secondary analyses, such as control_1/rmsd/
for the output of the analyze_rmsd script on the
control_1 dataset.

### Trace File

A trace JSON file is output such that a run of an 
experiment can be recorded and reproduced. This
records all steps performed by Workflow as well as
state changes and decisions. The file is intended
to be read/written by the utility while still being
understandable by a human.


## Data

Workflow's ExperimentManager maintains experiment state
in a data dictionary with name-value pairs. Any type of
data can be saved, but common types should be defined
as classes in the data/ directory. It uses dot notation
to represent nested data, which is recommended for saving
state that is specific to a particular step of the
experiment, or should be stored on consecutive runs of
the same step (e.g. step_1.my_data). A missing data is
represented by None so that should be checked for,
along with the type, as needed by the implementation
of the experiment parts. It is important to use the
API for reading inputs and writing outputs so as to
maintain a coherent state and record all data changes
to the trace file.


## Experiment Parts

Workflow's ExperimentManager conducts an experiment
as a sequence of steps and decision points. Each part
of the experiment needs a unique name identifier. Use
dot notation to refer to nested parts (e.g. flow_1.step_1).

A 'step' is usually a single analysis task. Each type
of step is defined as a class in the part_types/step directory.
Steps are intended as re-usable 'building blocks' and should
be small in scope. Each step can be configured with 'input_names'
and 'output_names' dictionaries, each mapping the names of data
in the manager's data dictionary to the argument names the
step implementation expects. Each step can also specify the 
'next_part' name of what to run automatically after the step
is finished.

A 'decision' is usually a single decision point, that
determines what step to do next in the experiment. Each
type of decision is defined as a class in the part_types/decision
directory. Decisions are intended as simple branches, like
if-else statements in the workflow. Each decision can be
configured with an 'input_names' dictionary (but no output_names
since a decision should not be changing data, only reading it to
make its choice). Each decision should also specify a 'next_part'
dictionary, mapping a part identifier to the route names the
decision implementation expects.

A 'flow' is a grouping of steps, decisions, and other flows.
Each type of flow is defined as a class in the part_types/flow
directory. Flows can be used to represent common sections of
experiments. Flows can also give special behavior to their
contained steps. For example, the 'parallel' flow runs all
the steps it contains in separate sub-processes to speed up
processing time.

If the manager encounters a situation where the 'next' part
of the experiment is None or invalid, or if a step/decision
crashes with an uncaught exception, it will prompt the
researcher to specify the identifier of the experiment
to go next or to end the experiment.

When adding a new step, decision, or flow be sure to put
the class name in the 'part_types' dictionary in part_types.py.
