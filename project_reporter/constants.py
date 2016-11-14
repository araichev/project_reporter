PROJECT_ATTRS = [
  'name',
  'description',
  'client',
  'budget',
  'currency',
  'tasks_df',
  'workers_df',
  'timesheet_df',
  ]

DTYPE = {
  'date': str,
  'task': 'category',
  'worker': 'category',
  'duration': float,
  'budget': float,
  'rate': float,
  }
