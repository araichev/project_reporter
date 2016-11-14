from pathlib import Path
import random
from collections import OrderedDict

import pandas as pd
import numpy as np
from highcharts import Highchart
import colorlover as cl
from xml.sax import ContentHandler, parse

import project_reporter.utilities as ut 
import project_reporter.constants as cs 

              
def compute_costs(project):
    """
    """
    if project.timesheet_df is None:
        raise ValueError('The project needs a timesheet for this operation')

    # Merge in billing rates and buget
    f = project.timesheet_df.merge(project.tasks_df).merge(project.workers_df)
    # Pandas bug: category dtypes not preserved.  So recreate them.
    f['task'] = f['task'].astype('category')
    f['worker'] = f['worker'].astype('category')
    f = f.rename(columns={'budget': 'task_budget'})
    
    # Compute cost
    f['cost'] = f['duration']*f['rate']
    f['cost/task_budget'] = f['cost']/f['task_budget']
    f['cost/project_budget'] = f['cost']/project.budget

    return f

def summarize(project, by_task=False, by_worker=False, freq=None):
    """
    """      
    if project.timesheet_df is None:
        raise ValueError('The project needs a timesheet for this operation')

    def my_agg(group):
        d = OrderedDict()
        d['duration'] = group['duration'].sum()
        d['rate'] = group['rate'].iat[0]
        d['cost'] = group['cost'].sum()
        d['task_budget'] = group['task_budget'].iat[0]
        return pd.Series(d)
    
    f = compute_costs(project)
    cols = []
    if by_task:
        cols.append('task')
    if by_worker:
        cols.append('worker')
    if freq is None:
        if cols:
            g = f.groupby(cols).apply(my_agg).reset_index()
        else:
            s = my_agg(f)
            g = pd.DataFrame([s.values], columns=s.index)
    else:
        cols.insert(0, pd.TimeGrouper(freq, label='left'))
        g = f.set_index('date').groupby(cols).apply(my_agg).reset_index()
            
    # Append or drop some columns
    if by_task:
        g['cost/task_budget'] = g['cost']/g['task_budget']
        g['cost/project_budget'] = g['cost']/project.budget
    else:
        g = g.drop(['task_budget'], axis=1)
        g['cost/project_budget'] = g['cost']/project.budget
    if not by_worker:
        g = g.drop(['rate'], axis=1)
    return g

def plot(project, freq=None):
    """
    """
    if project.timesheet_df is None:
        raise ValueError('The project needs a timesheet for this operation')

    f = summarize(project, by_task=True, by_worker=True, freq=freq)
    f['cost/project_budget'] *= 100 # For percentages

    chart = Highchart()
    colors = ut.get_colors(0.8)
    options = {
        'chart': {
            'width': 600,
            'height': 400,
        },
        'colors': colors,
        'title': {
            'text': project.name
        },
        'subtitle': {
            'text': 'Click on dates or columns for worker profiles'
        },
        'xAxis': {
            'type': 'category'
        },
        'yAxis': {
            'title': {
                'text': 'Cost as percentage project budget',
            },
            'min': 0, 
            'tickInterval': 10,
            'plotLines': [{
                'color': 'red', 
                'value': 100, 
                'width': 2, 
                }],
        },
        'tooltip': {
            'headerFormat': '<b>{point.key}</b><table>',
            'pointFormat': '<tr><td style="padding-right:1em">{series.name}</td>' +
                '<td style="text-align:right">{point.y:.0f}%</td></tr>',
            'footerFormat': '<tr><td><b>Total</b></td><td style="text-align:right"><b>{point.total:.0f}%</b></td></tr></table>',
            'shared': True,
            'useHTML': True,
        },
        'drilldown': {
            'activeAxisLabelStyle': {
                'cursor': 'pointer', 
                'color': '#333',
                'fontWeight': 'normal',
                "textDecoration": None,
            }
        },
        'plotOptions': {
            'column': {
                'stacking': 'normal',
                'pointPadding': 0,
                'borderWidth': 1,
                'borderColor': '#333',
            }
    
        }
    }
    chart.set_dict_options(options)        
    
    if freq is None:            
        # Add tasks with worker drilldown
        for task, g in f.groupby('task'):
            drilldown_id = task
            series = [{
              'name': 'Project to date',
              'y': g['cost/project_budget'].sum(),
              'drilldown': drilldown_id,
              }]
            chart.add_drilldown_data_set(
              g[['worker', 'cost/project_budget']].values.tolist(), 
              'column', name=task, id=drilldown_id)    
            chart.add_data_set(series, 'column', name=task)
    else:            
        # Convert dates to strings
        f['date'] = f['date'].map(lambda x: x.strftime('%Y-%m-%d'))

        # Add tasks with worker drilldown
        for task, g in f.groupby('task'):
            series = []
            for date, gg in g.groupby('date'):
                drilldown_id = '{!s}-{!s}'.format(task, date)
                series.append({
                  'name': date,
                  'y': gg['cost/project_budget'].sum(),
                  'drilldown': drilldown_id,
                  })     
                chart.add_drilldown_data_set(
                  gg[['worker', 'cost/project_budget']].values.tolist(), 
                  'column', name=task, id=drilldown_id)
            chart.add_data_set(series, 'column', name=task)
            
    return chart

def plot_bak(project, freq=None):
    """
    """
    f = summarize(project, by_task=True, freq=freq)
    f['cost/project_budget'] *= 100  # For percentages

    chart = Highchart()
    colors = ut.get_colors(0.8)
    options = {
        'chart': {
            'width': 600,
            'height': 400,
        },
        'colors': colors,
        'title': {
            'text': project.name
        },
        'yAxis': {
            'title': {
                'text': 'Cost as percentage budget',
            },
            'min': 0, 
            'tickInterval': 10,
            'plotLines': [{
                'color': 'red', 
                'value': 100, 
                'width': 2, 
                }],
        },
        'tooltip': {
            'pointFormat': '<tr><td style="padding-right:1em">{series.name}</td>' +
                '<td style="text-align:right">{point.y:.0f}%</td></tr>',
            'footerFormat': '<tr><td><b>Total</b></td><td style="text-align:right"><b>{point.total:.0f}%</b></td></tr></table>',
            'shared': True,
            'useHTML': True,
        },
        'plotOptions': {
            'column': {
                'stacking': 'normal',
                'pointPadding': 0,
                'borderWidth': 1,
                'borderColor': '#333',
            }
    
        }
    }
    if freq is None:
        options['xAxis'] = {
            'categories': [project.name],
            'labels': {'enabled': False},
            }
        options['tooltip']['headerFormat'] = '<b>{point.x}</b><table>'
        chart.set_dict_options(options)        
            
        # Add tasks
        for task in f['task'].unique():
            g = f.loc[f['task'] == task, 'cost/project_budget']
            chart.add_data_set(g.values.tolist(), 'column', name=task)
    else:
        options['xAxis'] = {
            'type': 'datetime',
            'labels': {
                'format': '{value:%Y-%m-%d}',
                'rotation': -45,
                'align': 'right',
                },
            }
        options['tooltip']['headerFormat'] = '<b>{point.x:%Y-%m-%d}</b> (period start)<table>'
        chart.set_dict_options(options)        
            
        # Add tasks
        for task in f['task'].unique():
            g = f.loc[f['task'] == task, ['date', 'cost/project_budget']]
            chart.add_data_set(g.values.tolist(), 'column', name=task)
        
        

    return chart
