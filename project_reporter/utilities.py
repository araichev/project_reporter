import io

import pandas as pd
import colorlover as cl


def parse_df(csv_text, **kwargs):
    """
    Given a CSV text with a header, convert it to a data frame and
    return the result. 
    """
    csv = io.StringIO(csv_text)
    return pd.read_table(csv, sep=',', **kwargs)

def add_opacity(rgb_str, opacity):
    return 'rgba(' + rgb_str[4:-1] + ',{!s})'.format(opacity)

def get_colors(opacity=1):
    """
    Return a list of 10 nice qualitative-scale RGBA color strings of the form 'rgba(*,*,*,*)' and with the given opacity.
    """
    n = 10
    return [add_opacity(x, opacity) 
      for x in cl.scales[str(n)]['qual']['Set3']]
