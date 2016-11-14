from pathlib import Path

import pandas as pd
from xml.sax import ContentHandler, parse

import project_reporter.utilities as ut 

    
class ExcelHandler(ContentHandler):
    """
    Reference https://stackoverflow.com/questions/33470130/read-excel-xml-xls-file-with-pandas
    """
    def __init__(self):
        self.chars = [  ]
        self.cells = [  ]
        self.rows = [  ]
        self.tables = [  ]
        
    def characters(self, content):
        self.chars.append(content)
    
    def startElement(self, name, atts):
        if name=="Cell":
            self.chars = [  ]
        elif name=="Row":
            self.cells=[  ]
        elif name=="Table":
            self.rows = [  ]
    
    def endElement(self, name):
        if name=="Cell":
            self.cells.append(''.join(self.chars))
        elif name=="Row":
            self.rows.append(self.cells)
        elif name=="Table":
            self.tables.append(self.rows)

def read_replicon(path, header_row=11, start_row=13, end_row=None, 
  start_column=1, end_column=None):
    """
    Read a Replicon timesheet (Excel XML file) located at the given path (string or Path object).
    Assume that:
    
    - the header row starts at row ``header_row`` and extends from column ``start_column`` to column ``end_column``
    - the data is rectangular in shape, starts at row ``start_row`` and column ``start_column``, and ends at row ``end_row`` and column ``end_column`` 

    Here row and column numbers start at zero and setting the end row or end column to ``None`` means reading to the last row or last column, respectively, of the file.
    
    Return a Pandas data frame representing the timesheet data and header.
    """
    path = Path(path)
    excel = ExcelHandler()
    parse(str(path), excel)
    table = excel.tables[0]
    columns = [x.strip() for x in table[header_row][start_column:end_column]]
    data = [[y.strip() for y in x[start_column:end_column]] 
      for x in table[start_row:end_row]]
    f = pd.DataFrame(data, columns=columns)
    
    return f

def reformat_replicon(replicon_df):
    """
    Given a Replicon data frame (in the form output by :func:`read_replicon`) that contains at least the columns
    
    - ``'Entry Date'``
    - ``'Task Name'``
    - ``'User Name'``
    - ``'Billable Hrs'``

    convert it into a standard timesheet data frame, that is, one with at the columns
    
    - ``'date'``: datetime object
    - ``'task'``
    - ``'worker'``
    - ``'duration'``.
    
    Return the resulting data frame.
    """
    f = replicon_df.copy()
    
    # Drop extraneous columns
    drop_cols = [
        'Client Name', 
        'Non-Billable Hrs', 
        'Total Hrs',
        'Employee Id',
        ]
    f = f.drop(drop_cols, axis=1, errors='ignore')
    
    # Rename columns
    f = f.rename(columns={c: c.lower().strip().replace(' ', '_') 
      for c in f.columns})
    f = f.rename(columns={
        'task_name': 'task',
        'user_name': 'worker',
        'billable_hrs': 'duration',
        'entry_date': 'date'
        })
    
    # Fix dtypes
    f['date'] = pd.to_datetime(f['date'])
    f['duration'] = f['duration'].astype(float)
    
    # Clean worker
    def clean_worker(x):
        names = x.split(', ')
        if len(names) >= 2:
            names = names[::-1]
        return ' '.join(names).strip()
    
    f['worker'] = f['worker'].map(clean_worker)
    
    # Restrict columns
    new_cols = ['date', 'task', 'worker', 'duration']
    return f[new_cols].copy()
