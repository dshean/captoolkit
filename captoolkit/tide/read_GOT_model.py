#!/usr/bin/env python
# -*- coding: utf-8 -*-
u"""
read_GOT_model.py (11/2019)
Reads files for Richard Ray's Global Ocean Tide (GOT) models and makes initial
    calculations to run the tide program
Includes functions to extract tidal harmonic constants out of a tidal model for
    given locations

Input:
    ilon: longitude to interpolate
    ilat: latitude to interpolate
    directory: data directory for tide data files
    model_files: list of gzipped model files for each constituent

Options:
    METHOD: interpolation method
        spline: scipy bivariate spline interpolation
        linear, cubic, nearest: scipy griddata interpolations
    SCALE: scaling factor for converting to output units

Requires::
    numpy: Scientific Computing Tools For Python
        http://www.numpy.org
        http://www.scipy.org/NumPy_for_Matlab_Users
    scipy: Scientific Tools for Python
        http://www.scipy.org/

History:
    Updated 11/2019: find invalid mask points for each constituent
    Updated 09/2019: output as numpy masked arrays instead of nan-filled arrays
    Updated 07/2019: interpolate fill value mask with bivariate splines
    Updated 12/2018: python3 compatibility updates for division and zip
    Updated 10/2018: added SCALE as load tides are in mm and ocean are in cm
    Updated 08/2018: added multivariate spline interpolation option
    Written 07/2018
"""
from __future__ import division

import os
import gzip
import numpy as np
import scipy.interpolate

# PURPOSE: extract tidal harmonic constants out of GOT model at coordinates
def extract_GOT_constants(ilon,ilat,directory,model_files,METHOD='',SCALE=1):
    # adjust longitudinal convention of input latitude and longitude
    # to fit tide model convention
    if (np.min(ilon) < 0.0):
        lt0, = np.nonzero(ilon < 0)
        ilon[lt0] += 360.0

    # number of points
    npts = len(ilon)
    # amplitude and phase
    nc = len(model_files)
    ampl = np.ma.zeros((npts,nc))
    ampl.mask = np.zeros((npts,nc),dtype=np.bool)
    phase = np.ma.zeros((npts,nc))
    phase.mask = np.zeros((npts,nc),dtype=np.bool)
    # read and interpolate each constituent
    for i,model_file in enumerate(model_files):
        # read constituent from elevation file
        amp,ph,lon,lat = read_GOT_grid(os.path.join(directory,model_file))
        # grid step size of tide model
        dlon = np.abs(lon[1] - lon[0])
        dlat = np.abs(lat[1] - lat[0])
        # replace original values with extend matrices
        lon = extend_array(lon,dlon)
        amp = extend_matrix(amp)
        ph = extend_matrix(ph)
        # interpolate amplitude and phase of the constituent
        if (METHOD == 'spline'):
            # interpolate amplitude and phase of the constituent with scipy
            f1 = scipy.interpolate.RectBivariateSpline(lon,lat,amp.data.T,kx=1,ky=1)
            f2 = scipy.interpolate.RectBivariateSpline(lon,lat,amp.mask.T,kx=1,ky=1)
            f3 = scipy.interpolate.RectBivariateSpline(lon,lat,ph.data.T,kx=1,ky=1)
            f4 = scipy.interpolate.RectBivariateSpline(lon,lat,ph.mask.T,kx=1,ky=1)
            ampl.data[:,i] = f1.ev(ilon,ilat)
            ampl.mask[:,i] = f2.ev(ilon,ilat).astype(np.bool)
            phase.data[:,i] = f3.ev(ilon,ilat)
            phase.mask[:,i] = f4.ev(ilon,ilat).astype(np.bool)
            # mask invalid values
            ampl.data[ampl.mask[:,i],i] = ampl.fill_value
            phase.data[phase.mask[:,i],i] = phase.fill_value
        else:
            # create mesh grids of latitude and longitude
            X,Y = np.meshgrid(lon,lat)
            interp_points = zip(X.flatten(),Y.flatten())
            # replace invalid values with nan
            amp[amp==fv] = np.nan
            ph[ph==fv] = np.nan
            # interpolate amplitude and phase of the constituent with scipy
            ampl[:,i] = scipy.interpolate.griddata(interp_points, amp.flatten(),
                zip(X.flatten(),Y.flatten()), method=METHOD)
            phase[:,i] = scipy.interpolate.griddata(interp_points, ph.flatten(),
                zip(X.flatten(),Y.flatten()), method=METHOD)
            # mask invalid values
            ampl.mask[:,i] = np.isnan(ampl.data[:,i])
            phase.mask[:,i] = np.isnan(phase.data[:,i])
            ampl.data[ampl.mask[:,i],i] = ampl.fill_value
            phase.data[phase.mask[:,i],i] = phase.fill_value
    # convert amplitude from input units to meters
    amplitude = ampl*SCALE
    # return the interpolated values
    return (amplitude,phase)

# PURPOSE: wrapper function to extend an array
def extend_array(input_array,step_size):
    n = len(input_array)
    temp = np.zeros((n+3),dtype=input_array.dtype)
    temp[0] = input_array[0] - step_size
    temp[1:-2] = input_array[:]
    temp[-2] = input_array[-1] + step_size
    temp[-1] = input_array[-1] + 2.0*step_size
    return temp

# PURPOSE: wrapper function to extend a matrix
def extend_matrix(input_matrix):
    ny,nx = np.shape(input_matrix)
    temp = np.ma.zeros((ny,nx+3),dtype=input_matrix.dtype)
    temp[:,0] = input_matrix[:,-1]
    temp[:,1:-2] = input_matrix[:,:]
    temp[:,-2] = input_matrix[:,0]
    temp[:,-1] = input_matrix[:,1]
    return temp

# PURPOSE: read GOT model grid files
def read_GOT_grid(input_file):
    # read GZIP file
    with gzip.open(os.path.expanduser(input_file),'rb') as f:
        file_contents = f.read().splitlines()
    # parse header text
    nlat,nlon = np.array(file_contents[2].split(), dtype=np.int)
    ilat = np.array(file_contents[3].split(), dtype=np.float)
    ilon = np.array(file_contents[4].split(), dtype=np.float)
    fill_value = np.array(file_contents[5].split(), dtype=np.float)
    # create output variables
    lat = np.linspace(ilat[0],ilat[1],nlat)
    lon = np.linspace(ilon[0],ilon[1],nlon)
    amp = np.ma.zeros((nlat,nlon),fill_value=fill_value[0],dtype=np.float)
    ph = np.ma.zeros((nlat,nlon),fill_value=fill_value[0],dtype=np.float)
    # create masks for output variables (0=valid)
    amp.mask = np.zeros((nlat,nlon),dtype=np.bool)
    ph.mask = np.zeros((nlat,nlon),dtype=np.bool)
    # starting lines to fill amplitude and phase variables
    l1 = 7
    l2 = 14 + np.int(nlon//11)*nlat + nlat
    # for each latitude
    for i in range(nlat):
        for j in range(nlon//11):
            j1 = j*11
            amp.data[i,j1:j1+11] = np.array(file_contents[l1].split(),dtype='f')
            ph.data[i,j1:j1+11] = np.array(file_contents[l2].split(),dtype='f')
            l1 += 1
            l2 += 1
        # add last tidal variables
        j1 = (j+1)*11; j2 = nlon % 11
        amp.data[i,j1:j1+j2] = np.array(file_contents[l1].split(),dtype='f')
        ph.data[i,j1:j1+j2] = np.array(file_contents[l2].split(),dtype='f')
        l1 += 1
        l2 += 1
    # set masks
    amp.mask[amp.data == amp.fill_value] = True
    ph.mask[ph.data == ph.fill_value] = True
    # return output variables
    return (amp,ph,lon,lat)
