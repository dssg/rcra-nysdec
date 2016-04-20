import logging
from datetime import date
import pandas as pd

from drain.util import day
from drain.data import FromSQL
from drain.aggregate import Aggregate, Count
from drain.aggregation import SpacetimeAggregation

class RmpAggregation(SpacetimeAggregation):
    def __init__(self, spacedeltas, dates, **kwargs):
        SpacetimeAggregation.__init__(self, spacedeltas=spacedeltas, dates=dates, 
                prefix='rmp', date_column='actual_end_date', **kwargs)

        if not self.parallel:
            self.inputs = [FromSQL(table='output.rmp', 
                    parse_dates=['actual_end_date'], target=True)]

    def get_aggregates(self, date, delta):
        booleans = [c for c in self.inputs[0].get_result().columns
                if c not in ('rmp_id', 'rcra_id', 'actual_end_date')]

        aggregates = [
            Count(),
            Count(booleans, prop=True),
            Aggregate(lambda i: (date - i.actual_end_date) / day, 
                    ['min', 'max'], name='actual_end_date')
        ]

        return aggregates

    def fillna_value(self, df, left, **concat_args):
        return pd.Series(0, index=df.columns)