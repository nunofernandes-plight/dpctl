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

# distutils: language = c++
# cython: language_level=3
# cython: linetrace=True

"""Implements a Python interface for SYCL's program and kernel runtime classes.

The module also provides functions to create a SYCL program from either
a OpenCL source string or a SPIR-V binary file.

"""

cimport cython.array

from dpctl._backend cimport (  # noqa: E211, E402
    DPCTLCString_Delete,
    DPCTLKernel_Delete,
    DPCTLKernel_GetNumArgs,
    DPCTLKernelBundle_CreateFromOCLSource,
    DPCTLKernelBundle_CreateFromSpirv,
    DPCTLKernelBundle_Delete,
    DPCTLKernelBundle_GetKernel,
    DPCTLKernelBundle_HasKernel,
    DPCTLSyclContextRef,
    DPCTLSyclDeviceRef,
    DPCTLSyclKernelBundleRef,
    DPCTLSyclKernelRef,
)

__all__ = [
    "create_program_from_source",
    "create_program_from_spirv",
    "SyclKernel",
    "SyclProgram",
    "SyclProgramCompilationError",
]

cdef class SyclProgramCompilationError(Exception):
    """This exception is raised when a ``sycl::kernel_bundle`` could not be
       built from either a SPIR-V binary file or a string source.
    """
    pass


cdef class SyclKernel:
    """
    """
    @staticmethod
    cdef SyclKernel _create(DPCTLSyclKernelRef kref, str name):
        cdef SyclKernel ret = SyclKernel.__new__(SyclKernel)
        ret._kernel_ref = kref
        ret._function_name = name
        return ret

    def __dealloc__(self):
        DPCTLKernel_Delete(self._kernel_ref)

    def get_function_name(self):
        """ Returns the name of the ``sycl::kernel`` function.
        """
        return self._function_name

    def get_num_args(self):
        """ Returns the number of arguments for this kernel function.
        """
        return DPCTLKernel_GetNumArgs(self._kernel_ref)

    cdef DPCTLSyclKernelRef get_kernel_ref(self):
        """ Returns the ``DPCTLSyclKernelRef`` pointer for this SyclKernel.
        """
        return self._kernel_ref

    def addressof_ref(self):
        """ Returns the address of the C API ``DPCTLSyclKernelRef`` pointer
        as a ``size_t``.

        Returns:
            The address of the ``DPCTLSyclKernelRef`` pointer used to create
            this :class:`dpctl.SyclKernel` object cast to a ``size_t``.
        """
        return int(<size_t>self._kernel_ref)


cdef class SyclProgram:
    """ Wraps a ``sycl::kernel_bundle<sycl::bundle_state::executable>`` object
    created using SYCL interoperability layer with underlying backends. Only the
    OpenCL and Level-Zero backends are currently supported.

    SyclProgram exposes the C API from ``dpctl_sycl_kernel_bundle_interface.h``.
    A SyclProgram can be created from either a source string or a SPIR-V
    binary file.
    """

    @staticmethod
    cdef SyclProgram _create(DPCTLSyclKernelBundleRef KBRef):
        cdef SyclProgram ret = SyclProgram.__new__(SyclProgram)
        ret._program_ref = KBRef
        return ret

    def __dealloc__(self):
        DPCTLKernelBundle_Delete(self._program_ref)

    cdef DPCTLSyclKernelBundleRef get_program_ref(self):
        return self._program_ref

    cpdef SyclKernel get_sycl_kernel(self, str kernel_name):
        name = kernel_name.encode('utf8')
        return SyclKernel._create(
            DPCTLKernelBundle_GetKernel(self._program_ref, name),
            kernel_name
        )

    def has_sycl_kernel(self, str kernel_name):
        name = kernel_name.encode('utf8')
        return DPCTLKernelBundle_HasKernel(self._program_ref, name)

    def addressof_ref(self):
        """Returns the address of the C API DPCTLSyclKernelBundleRef pointer
        as a long.

        Returns:
            The address of the ``DPCTLSyclKernelBundleRef`` pointer used to
            create this :class:`dpctl.SyclProgram` object cast to a ``size_t``.
        """
        return int(<size_t>self._program_ref)


cpdef create_program_from_source(SyclQueue q, unicode src, unicode copts=""):
    """
        Creates a Sycl interoperability program from an OpenCL source string.

        We use the ``DPCTLKernelBundle_CreateFromOCLSource()`` C API function
        to create a ``sycl::kernel_bundle<sycl::bundle_state::executable>``
        from an OpenCL source program that can contain multiple kernels.
        Note: This function is currently only supported for the OpenCL backend.

        Parameters:
            q (SyclQueue)   : The :class:`SyclQueue` for which the
                              :class:`SyclProgram` is going to be built.
            src (unicode): Source string for an OpenCL program.
            copts (unicode) : Optional compilation flags that will be used
                              when compiling the program.

        Returns:
            program (SyclProgram): A :class:`SyclProgram` object wrapping the
            ``sycl::kernel_bundle<sycl::bundle_state::executable>`` returned
            by the C API.

        Raises:
            SyclProgramCompilationError: If a SYCL kernel bundle could not be
            created.
    """

    cdef DPCTLSyclKernelBundleRef KBref
    cdef bytes bSrc = src.encode('utf8')
    cdef bytes bCOpts = copts.encode('utf8')
    cdef const char *Src = <const char*>bSrc
    cdef const char *COpts = <const char*>bCOpts
    cdef DPCTLSyclContextRef CRef = q.get_sycl_context().get_context_ref()
    cdef DPCTLSyclDeviceRef DRef = q.get_sycl_device().get_device_ref()
    KBref = DPCTLKernelBundle_CreateFromOCLSource(CRef, DRef, Src, COpts)

    if KBref is NULL:
        raise SyclProgramCompilationError()

    return SyclProgram._create(KBref)


cpdef create_program_from_spirv(SyclQueue q, const unsigned char[:] IL,
                                unicode copts=""):
    """
        Creates a Sycl interoperability program from an SPIR-V binary.

        We use the ``DPCTLKernelBundle_CreateFromOCLSpirv()`` C API function to
        create a ``sycl::kernel_bundle<sycl::bundle_state::executable>`` object
        from an compiled SPIR-V binary file.

        Parameters:
            q (SyclQueue): The :class:`SyclQueue` for which the
                           :class:`SyclProgram` is going to be built.
            IL (const char[:]) : SPIR-V binary IL file for an OpenCL program.
            copts (unicode) : Optional compilation flags that will be used
                              when compiling the program.

        Returns:
            program (SyclProgram): A :class:`SyclProgram` object wrapping the
            ``sycl::kernel_bundle<sycl::bundle_state::executable>`` returned by
            the C API.

        Raises:
            SyclProgramCompilationError: If a SYCL kernel bundle could not be
            created.
    """

    cdef DPCTLSyclKernelBundleRef KBref
    cdef const unsigned char *dIL = &IL[0]
    cdef DPCTLSyclContextRef CRef = q.get_sycl_context().get_context_ref()
    cdef DPCTLSyclDeviceRef DRef = q.get_sycl_device().get_device_ref()
    cdef size_t length = IL.shape[0]
    cdef bytes bCOpts = copts.encode('utf8')
    cdef const char *COpts = <const char*>bCOpts
    KBref = DPCTLKernelBundle_CreateFromSpirv(
        CRef, DRef, <const void*>dIL, length, COpts
    )
    if KBref is NULL:
        raise SyclProgramCompilationError()

    return SyclProgram._create(KBref)
