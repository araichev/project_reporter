"""
This module implements projects.
A *project* is a collection of attributes (name, budget, tasks, workers, etc.) and an optional timesheet describing task work done over a certain time period.

CONVENTIONS:
    - All data frames mentioned below are Pandas DataFrame objects

"""
from pathlib import Path

import voluptuous as vt
import magic
import yaml
import pandas as pd
import numpy as np

import project_reporter.constants as cs 
import project_reporter.utilities as ut
import project_reporter.replicon as rp 


class Project(object):
    """
    This class encodes a project.
    Each instance has the following properties.

    - ``name``: string; name of project
    - ``'description'``: string; description of project
    - ``'client'``: string; name of project client 
    - ``'budget'``: positive float; project budget 
    - ``'currency'``: string; project currency units, e.g. 'NZD'
    - ``'tasks_df'``: data frame; should contain the columns 
        
        * ``'task'``: string; task description
        * ``'budget'``: positive float; budget for task 

      Also, the sum of the task budget should less than or equal to the  project budget
    - ``'workers_df'``: data frame; should contain the columns

        * ``'worker'``: string; name of the project worker 
        * ``'rate'``: positive float; hourly rate of the worker

    - ``'timesheet_df'`` (optional): data frame; defaults to ``None``; should contain the columns

        * ``'date'``: datetime object; date work was done
        * ``'task'``: project task the work was for
        * ``'worker'``: project worker 
        * ``'duration'``: duration in hours of the work

    """

    def __init__(self, name, description, client, budget, currency, 
      tasks_df, workers_df, timesheet_df=None):
        """
        """
        self.name = check_str(name)
        self.description = check_str(description)
        self.client = check_str(client)
        self.budget = check_pos(budget)                       
        self.currency = check_str(currency)
        self.tasks_df = check_tasks_df(tasks_df, budget)
        self.workers_df = check_workers_df(workers_df)
        self.timesheet_df = check_timesheet_df(timesheet_df, tasks_df,
          workers_df)
        
    def __repr__(self):
        result = []
        for attr in cs.PROJECT_ATTRS:
            val = getattr(self, attr)
            if attr == 'timesheet_df':
                attr = 'timesheet_df (head)'
                val = val.head()
            s = '{!s}: {!s}\n'.format(attr, val)
            result.append(s)
        return '\n'.join(result)

    def copy(self):
        """
        Return a copy of this project, that is, a project with all the same attributes.
        """
        other = Project()
        for key in cs.PROJECT_ATTRS:
            value = getattr(self, key)
            if isinstance(value, pd.DataFrame):
                # Pandas copy data frame
                value = value.copy()
            setattr(other, key, value)
        
        return other


# ------------
# IO functions
# ------------
def read_config(config_path):
    """
    Read a YAML project configuration file located at the given path.
    Parse the file, converting some keys to data frames, and returning the resulting dictionary. 

    The configuration file must have all the keys listed in the Project class description except for ``timesheet_df``.
    Also, ``tasks_df`` and ``workers_df`` should be CSV strings.
    Here is an example YAML configuration string:: 

        name: Project A
        description: "Suppress the pirates, who have been raiding ships for months"
        client:  Hong Kong Marine Police
        budget: 40000
        currency: HKD
        tasks_df: |
            task,budget
            Inception,2000
            Context,3000
            Problems & Opportunities,20000
            Solutions,10000
            Project Management,5000
        workers_df: |
            worker,rate
            Captain Chi,200
            Dragon Ma,190
            Hong Tin-tsu,180
            Fei,170
            Winnie,160

    """
    path = Path(config_path)
    with path.open() as src:
        d = yaml.load(src)

    # Parse tasks and workers
    if 'tasks_df' in d:
        d['tasks_df'] = ut.parse_df(d['tasks_df'], dtype=cs.DTYPE)

    if 'workers_df' in d:
        d['workers_df'] = ut.parse_df(d['workers_df'], dtype=cs.DTYPE)

    return d

def read_timesheet(timesheet_path, replicon_options=None):
    """
    Read a CSV or a Replicon XML timesheet file located at the given path.
    Convert the file to a data frame and return the result.

    A CSV timesheet should have the columns specified in the Project class docstring.
    A Replicon XML file should have the columns specified in the docstring for the function :func:`replicon.read_replicon`.
    That function is called with the dictionary of options ``replicon_options`` in case a Replicon XML is given.  
    """
    path = Path(timesheet_path)
    mime_type = magic.from_file(str(path), mime=True)

    if 'xml' in mime_type:
        # Replicon time sheet
        if replicon_options is None:
            replicon_options = {}
        f = rp.read_replicon(path, **replicon_options) 
        f = rp.reformat_replicon(f)
    elif 'text' in mime_type:
        f = pd.read_csv(path, dtype=cs.DTYPE, parse_dates=['date'])
    else:
        raise TypeError('{!s} not a recognized file format'.format(path))

    return f 

def read_project(config_path, timesheet_path=None, replicon_options=None):
    """
    Read a project dictionary from a YAML file located at the path ``config_path``, and read a project timesheet from the path ``timesheet_path``.
    Parse these files, check them, and, if successful, return a corresponding Project instance.
    """
    project_dict = read_config(config_path)
    if timesheet_path is not None:
        project_dict['timesheet_df'] = read_timesheet(timesheet_path,
          replicon_options=replicon_options)

    return Project(**project_dict)

def write_project(project, config_path, timesheet_path=None):
    """
    """
    pass

# ---------------
# Format checkers
# ---------------
check_str = vt.Schema(str)
check_pos = vt.Schema(vt.Range(min=0))
check_df_instance = vt.Schema(pd.DataFrame)

def df_nonempty(f):
    if f.empty:
        raise vt.Invalid("Not a nonempty data frame")
    return f 

check_df_nonempty = vt.Schema(df_nonempty)

def check_df_header(f, expect_cols):
    if set(f.columns) != set(expect_cols):
        raise vt.Invalid("Data frame lacks the correct header of {!s}".
          format(set(expect_cols)))
    return f

def df_no_nans(f):
    for col in f.columns:
        if f[col].isnull().sum() != 0:
            raise vt.Invalid("NaNs found")
    return f

check_df_no_nans = vt.Schema(df_no_nans)

def check_df(f, expect_cols):
    f = check_df_instance(f)
    f = check_df_header(f, expect_cols)
    f = check_df_no_nans(f)    
    return f 

def check_tasks_df(f, budget):
    f = check_df(f, ['task', 'budget'])

    # Check data types 
    for v in f['budget'].values:
        if not isinstance(v, float):
            raise vt.Invalid('Found the non-numerical value {!s}'.\
              format(v))

    # Check budget not exceeded
    b = f['budget'].sum()
    if b != budget:
        raise vt.Invalid('Task budgets sum to {!s} '\
          'which does not equal the project budget of {!s}'.format(
          b, budget))

    return f

def check_workers_df(f):
    f = check_df(f, ['worker', 'rate'])

    # Check data types 
    for v in f['rate'].values:
        if not isinstance(v, float):
            raise vt.Invalid('Found the non-numerical value {!s}'.\
              format(v))

    return f

def check_timesheet_df(timesheet_df, tasks_df, workers_df):
    f = timesheet_df.copy()
    if f is None:
        return f 

    f = check_df(f, ['date', 'task', 'worker', 'duration'])

    # Check data types 
    for v in f['duration'].values:
        if not isinstance(v, float):
            raise vt.Invalid('{!s} has the non-numerical value {!s}'.\
              format(name, v))

    # Check tasks
    D = set(f['task']) - set(tasks_df['task'])
    if D:
        raise vt.Invalid(
          'Found tasks not in the project config: {!s}'.format(D))

    # Check workers
    D = set(f['worker']) - set(workers_df['worker'])
    if D:
        raise vt.Invalid(
          'Found workers not in the project config: {!s}'.format(D))

    return f 