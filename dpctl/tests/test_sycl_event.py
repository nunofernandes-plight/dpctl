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

""" Defines unit test cases for the SyclEventRaw class.
"""

import numpy as np
import pytest

import dpctl
import dpctl.memory as dpctl_mem
import dpctl.program as dpctl_prog
from dpctl import event_status_type as esty

from ._helper import has_cpu


def produce_event(profiling=False):
    oclSrc = "                                                                 \
            kernel void add(global int* a) {                                   \
                size_t index = get_global_id(0);                               \
                a[index] = a[index] + 1;                                       \
            }"
    if profiling:
        q = dpctl.SyclQueue("opencl:cpu", property="enable_profiling")
    else:
        q = dpctl.SyclQueue("opencl:cpu")
    prog = dpctl_prog.create_program_from_source(q, oclSrc)
    addKernel = prog.get_sycl_kernel("add")

    bufBytes = 1024 * np.dtype("i").itemsize
    abuf = dpctl_mem.MemoryUSMShared(bufBytes, queue=q)
    a = np.ndarray((1024), buffer=abuf, dtype="i")
    a[:] = np.arange(1024)
    args = []

    args.append(a.base)
    r = [1024]
    ev = q.submit(addKernel, args, r)

    return ev


def test_create_default_event_raw():
    try:
        dpctl.SyclEventRaw()
    except ValueError:
        pytest.fail("Failed to create a default event")


def test_create_event_raw_from_SyclEvent():
    if has_cpu():
        ev = produce_event()
        try:
            dpctl.SyclEventRaw(ev)
        except ValueError:
            pytest.fail("Failed to create an event from SyclEvent")
    else:
        pytest.skip("No OpenCL CPU queues available")


def test_create_event_raw_from_capsule():
    try:
        event = dpctl.SyclEventRaw()
        event_capsule = event._get_capsule()
        dpctl.SyclEventRaw(event_capsule)
    except ValueError:
        pytest.fail("Failed to create an event from capsule")


def test_wait_with_event():
    event = dpctl.SyclEventRaw()
    try:
        dpctl.SyclEventRaw.wait(event)
    except ValueError:
        pytest.fail("Failed to wait for the event")


def test_wait_with_list():
    event_1 = dpctl.SyclEventRaw()
    event_2 = dpctl.SyclEventRaw()
    try:
        dpctl.SyclEventRaw.wait([event_1, event_2])
    except ValueError:
        pytest.fail("Failed to wait for events from the list")


def test_execution_status():
    event = dpctl.SyclEventRaw()
    try:
        event_status = event.execution_status
    except ValueError:
        pytest.fail("Failed to get an event status")
    assert event_status == esty.complete


def test_backend():
    try:
        dpctl.SyclEventRaw().backend
    except ValueError:
        pytest.fail("Failed to get backend from event")


@pytest.mark.skip(reason="event::get_wait_list() method returns wrong result")
def test_get_wait_list():
    if has_cpu():
        oclSrc = "                                                             \
            kernel void add_k(global float* a) {                               \
                size_t index = get_global_id(0);                               \
                a[index] = a[index] + 1;                                       \
            }                                                                  \
            kernel void sqrt_k(global float* a) {                              \
                size_t index = get_global_id(0);                               \
                a[index] = sqrt(a[index]);                                     \
            }                                                                  \
            kernel void sin_k(global float* a) {                               \
                size_t index = get_global_id(0);                               \
                a[index] = sin(a[index]);                                      \
            }"
        q = dpctl.SyclQueue("opencl:cpu")
        prog = dpctl_prog.create_program_from_source(q, oclSrc)
        addKernel = prog.get_sycl_kernel("add_k")
        sqrtKernel = prog.get_sycl_kernel("sqrt_k")
        sinKernel = prog.get_sycl_kernel("sin_k")

        bufBytes = 1024 * np.dtype("f").itemsize
        abuf = dpctl_mem.MemoryUSMShared(bufBytes, queue=q)
        a = np.ndarray((1024), buffer=abuf, dtype="f")
        a[:] = np.arange(1024)
        args = []

        args.append(a.base)
        r = [1024]
        ev_1 = q.submit(addKernel, args, r)
        ev_2 = q.submit(sqrtKernel, args, r, dEvents=[ev_1])
        ev_3 = q.submit(sinKernel, args, r, dEvents=[ev_2])

        ev_raw = dpctl.SyclEventRaw(ev_3)

        try:
            wait_list = ev_raw.get_wait_list()
        except ValueError:
            pytest.fail(
                "Failed to get a list of waiting events from SyclEventRaw"
            )
        assert len(wait_list)


def test_profiling_info():
    if has_cpu():
        event = produce_event(profiling=True)
        event_raw = dpctl.SyclEventRaw(event)
        assert event_raw.profiling_info_submit
        assert event_raw.profiling_info_start
        assert event_raw.profiling_info_end
    else:
        pytest.skip("No OpenCL CPU queues available")
