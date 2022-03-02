#                      Data Parallel Control (dpctl)
#
# Copyright 2020-2021 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import numpy as np
import pytest
from numpy.testing import assert_array_equal

import dpctl
import dpctl.tensor as dpt


def test_permute_dims_incorrect_type():
    X_list = list([[1, 2, 3], [4, 5, 6]])
    X_tuple = tuple(X_list)
    Xnp = np.array(X_list)

    pytest.raises(TypeError, dpt.permute_dims, X_list, (1, 0))
    pytest.raises(TypeError, dpt.permute_dims, X_tuple, (1, 0))
    pytest.raises(TypeError, dpt.permute_dims, Xnp, (1, 0))


def test_permute_dims_empty_array():
    try:
        q = dpctl.SyclQueue()
    except dpctl.SyclQueueCreationError:
        pytest.skip("Queue could not be created")

    Xnp = np.empty((10, 0))
    X = dpt.asarray(Xnp, sycl_queue=q)
    Y = dpt.permute_dims(X, (1, 0))
    Ynp = np.transpose(Xnp, (1, 0))
    assert_array_equal(Ynp, dpt.asnumpy(Y))


def test_permute_dims_0d_1d():
    try:
        q = dpctl.SyclQueue()
    except dpctl.SyclQueueCreationError:
        pytest.skip("Queue could not be created")

    Xnp_0d = np.array(1, dtype="int64")
    X_0d = dpt.asarray(Xnp_0d, sycl_queue=q)
    Y_0d = dpt.permute_dims(X_0d, ())
    assert_array_equal(dpt.asnumpy(Y_0d), dpt.asnumpy(X_0d))

    Xnp_1d = np.random.randint(0, 2, size=6, dtype="int64")
    X_1d = dpt.asarray(Xnp_1d, sycl_queue=q)
    Y_1d = dpt.permute_dims(X_1d, (0))
    assert_array_equal(dpt.asnumpy(Y_1d), dpt.asnumpy(X_1d))

    pytest.raises(ValueError, dpt.permute_dims, X_1d, ())
    pytest.raises(IndexError, dpt.permute_dims, X_1d, (1))
    pytest.raises(ValueError, dpt.permute_dims, X_1d, (1, 0))
    pytest.raises(
        ValueError, dpt.permute_dims, dpt.reshape(X_1d, (2, 3)), (1, 1)
    )


@pytest.mark.parametrize("shapes", [(2, 2), (1, 4), (3, 3, 3), (4, 1, 3)])
def test_permute_dims_2d_3d(shapes):
    try:
        q = dpctl.SyclQueue()
    except dpctl.SyclQueueCreationError:
        pytest.skip("Queue could not be created")

    Xnp_size = np.prod(shapes)

    Xnp = np.random.randint(0, 2, size=Xnp_size, dtype="int64").reshape(shapes)
    X = dpt.asarray(Xnp, sycl_queue=q)
    X_ndim = X.ndim
    if X_ndim == 2:
        Y = dpt.permute_dims(X, (1, 0))
        Ynp = np.transpose(Xnp, (1, 0))
    elif X_ndim == 3:
        X = dpt.asarray(Xnp, sycl_queue=q)
        Y = dpt.permute_dims(X, (2, 0, 1))
        Ynp = np.transpose(Xnp, (2, 0, 1))
    assert_array_equal(Ynp, dpt.asnumpy(Y))
