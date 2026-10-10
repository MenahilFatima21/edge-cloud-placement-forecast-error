"""Cache parsed BitBrain CSVs (performance only; data is byte-for-byte the same frame).

BitbrainWorkload2 calls pd.read_csv(path, sep=';\\t') -- a regex separator,
which forces pandas' slow Python parser. That accounts for ~85% of runtime
(500 files at start-up plus one per new task). We parse each file once into a
pickle; later reads load the pickle (~100x faster). No in-memory cache:
the laptop has 7.7 GB RAM shared by parallel runs.
"""
import os
import pandas as pd

_orig_read_csv = pd.read_csv


def _cached_read_csv(path, *args, **kwargs):
    p = str(path)
    if 'bitbrain' not in p or not p.endswith('.csv'):
        return _orig_read_csv(path, *args, **kwargs)
    cache_dir = os.path.join(os.path.dirname(p), '..', 'cache')
    pk = os.path.join(cache_dir, os.path.basename(p)[:-4] + '.pkl')
    if os.path.exists(pk):
        df = pd.read_pickle(pk)
    else:
        df = _orig_read_csv(path, *args, **kwargs)
        os.makedirs(cache_dir, exist_ok=True)
        tmp = pk + f'.{os.getpid()}.tmp'
        df.to_pickle(tmp); os.replace(tmp, pk)
    return df


def install():
    pd.read_csv = _cached_read_csv
