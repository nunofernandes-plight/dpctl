//===-- test_sycl_kernel_interface.cpp - Test cases for kernel interface  ===//
//
//                      Data Parallel Control (dpctl)
//
// Copyright 2020-2021 Intel Corporation
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//    http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
//===----------------------------------------------------------------------===//
///
/// \file
/// This file has unit test cases for functions defined in
/// dpctl_sycl_kernel_interface.h.
///
//===----------------------------------------------------------------------===//

#include "dpctl_sycl_context_interface.h"
#include "dpctl_sycl_device_interface.h"
#include "dpctl_sycl_device_selector_interface.h"
#include "dpctl_sycl_kernel_bundle_interface.h"
#include "dpctl_sycl_kernel_interface.h"
#include "dpctl_sycl_queue_interface.h"
#include "dpctl_sycl_queue_manager.h"
#include "dpctl_utils.h"
#include <CL/sycl.hpp>
#include <array>
#include <gtest/gtest.h>

using namespace cl::sycl;

namespace
{
struct TestDPCTLSyclKernelInterface
    : public ::testing::TestWithParam<const char *>
{
    const char *CLProgramStr = R"CLC(
        kernel void add(global int* a, global int* b, global int* c) {
            size_t index = get_global_id(0);
            c[index] = a[index] + b[index];
        }

        kernel void axpy(global int* a, global int* b, global int* c, int d) {
            size_t index = get_global_id(0);
            c[index] = a[index] + d*b[index];
        }
    )CLC";
    const char *CompileOpts = "-cl-fast-relaxed-math";
    DPCTLSyclDeviceSelectorRef DSRef = nullptr;
    DPCTLSyclDeviceRef DRef = nullptr;

    TestDPCTLSyclKernelInterface()
    {
        DSRef = DPCTLFilterSelector_Create(GetParam());
        DRef = DPCTLDevice_CreateFromSelector(DSRef);
    }

    ~TestDPCTLSyclKernelInterface()
    {
        DPCTLDeviceSelector_Delete(DSRef);
        DPCTLDevice_Delete(DRef);
    }

    void SetUp()
    {
        if (!DRef) {
            auto message = "Skipping as no device of type " +
                           std::string(GetParam()) + ".";
            GTEST_SKIP_(message.c_str());
        }
    }
};
} // namespace

TEST_P(TestDPCTLSyclKernelInterface, CheckGetNumArgs)
{
    auto QueueRef = DPCTLQueue_CreateForDevice(DRef, nullptr, 0);
    auto CtxRef = DPCTLQueue_GetContext(QueueRef);
    auto KBRef = DPCTLKernelBundle_CreateFromOCLSource(
        CtxRef, DRef, CLProgramStr, CompileOpts);
    auto AddKernel = DPCTLKernelBundle_GetKernel(KBRef, "add");
    auto AxpyKernel = DPCTLKernelBundle_GetKernel(KBRef, "axpy");

    ASSERT_EQ(DPCTLKernel_GetNumArgs(AddKernel), 3ul);
    ASSERT_EQ(DPCTLKernel_GetNumArgs(AxpyKernel), 4ul);

    DPCTLQueue_Delete(QueueRef);
    DPCTLContext_Delete(CtxRef);
    DPCTLKernelBundle_Delete(KBRef);
    DPCTLKernel_Delete(AddKernel);
    DPCTLKernel_Delete(AxpyKernel);
}

TEST_P(TestDPCTLSyclKernelInterface, CheckNullPtrArg)
{
    DPCTLSyclKernelRef AddKernel = nullptr;

    ASSERT_EQ(DPCTLKernel_GetNumArgs(AddKernel), -1);
}

INSTANTIATE_TEST_SUITE_P(TestKernelInterfaceFunctions,
                         TestDPCTLSyclKernelInterface,
                         ::testing::Values("opencl:gpu:0", "opencl:cpu:0"));
