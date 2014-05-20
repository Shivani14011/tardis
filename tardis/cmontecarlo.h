#ifndef TARDIS_CMONTECARLO_H
#define TARDIS_CMONTECARLO_H

#include <Python.h>
#include <numpy/arrayobject.h>

#define MISS_DISTANCE 1e99

/** Look for a place to insert a value in an inversely sorted float array.
 *
 * @param x an inversely (largest to lowest) sorted float array
 * @param x_insert a value to insert
 * @param imin lower bound
 * @param imax upper bound
 *
 * @return index of the next boundary to the left
 */
npy_int64 binary_search(npy_float64 *x, npy_float64 x_insert, npy_int64 imin, npy_int64 imax);

npy_float64 compute_distance2outer(npy_float64 r, npy_float64 mu, npy_float64 r_outer);

npy_float64 compute_distance2inner(npy_float64 r, npy_float64 mu, npy_float64 r_inner);

#endif // TARDIS_CMONTECARLO_H
