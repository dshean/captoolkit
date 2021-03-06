#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Adds dummy variables as 1d arrays to HDF5 files(s).

Example:
    python dummy.py -v mask h_ibe h_tide h_load -l 1.0 0.0 0.0 0.0 -n 16 \
            -f '/mnt/devon-r0/shared_data/data/Envisat/grounded/*_RM.h5'

Notes:
    * Need to use -f to pass files!
    * If too many input files, pass a string: "/path/to/files.*"

"""
import os
import sys
import h5py
import argparse
import numpy as np
from glob import glob


def get_args():
    """ Get command-line arguments. """
    parser = argparse.ArgumentParser(
            description=('Add dummy vars to several HDF5 files'
                         ' (use -f to pass files!!)'))

    parser.add_argument(
            '-f', metavar='file', dest='files', type=str, nargs='+',
            help='HDF5 file(s) to process (need to use -f)',
            default=[None], required=True,)

    parser.add_argument(
            '-v', metavar='var', dest='vnames', type=str, nargs='+',
            help=('name of variable(s) to add'),
            default=[None], required=True,)

    parser.add_argument(
            '-l', metavar='val', dest='values', type=float, nargs='+',
            help=('value(s) of variable(s) to add'),
            default=[None], required=True,)

    parser.add_argument(
            '-n', metavar='njobs', dest='njobs', type=int, nargs=1,
            help=('number of jobs for parallel processing'),
            default=[1],)

    return parser.parse_args()


def write_vars(fname, vnames, values):
    """ Writes vars w/values as 1d arrays to file. """

    with h5py.File(fname) as f:

        # Get length from first var in the file
        npts = list(f.values())[0].shape[0]

        for var,val in zip(vnames, values):
            f[var] = np.repeat(val, npts)


if __name__ == '__main__':

    args = get_args()
    infiles = args.files
    vnames = args.vnames
    values = args.values
    njobs = args.njobs[0]

    # In case a string is passed to avoid "Argument list too long"
    if len(infiles) == 1:
        infiles = glob(infiles[0])

    print('parameters:')
    for arg in list(vars(args).items()):
        print(arg)

    if njobs == 1:
        print('Running sequential code ...')
        [write_vars(f, vnames, values) for f in infiles]
    else:
        print(('Running parallel code (%d jobs) ...' % njobs))
        from joblib import Parallel, delayed
        Parallel(n_jobs=njobs, verbose=5)(
                delayed(write_vars)(f, vnames, values) for f in infiles)

    print(('Processed files:', len(infiles)))

