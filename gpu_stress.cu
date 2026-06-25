#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>

__global__ void saxpy_kernel(int n, float a, const float* x, float* y) {
    int idx = blockIdx.x * blockDim.x + threadIdx.x;
    if (idx < n) {
        y[idx] = a * x[idx] + y[idx];
    }
}

static void check_cuda(cudaError_t err, const char* msg) {
    if (err != cudaSuccess) {
        fprintf(stderr, "CUDA error at %s: %s\n", msg, cudaGetErrorString(err));
        exit(1);
    }
}

int main(int argc, char** argv) {
    int iterations = 1000000;
    if (argc > 1) {
        iterations = atoi(argv[1]);
        if (iterations < 1) {
            iterations = 1000000;
        }
    }

    int device_count = 0;
    check_cuda(cudaGetDeviceCount(&device_count), "cudaGetDeviceCount");
    if (device_count == 0) {
        fprintf(stderr, "No CUDA devices found\n");
        return 1;
    }

    cudaDeviceProp prop{};
    check_cuda(cudaGetDeviceProperties(&prop, 0), "cudaGetDeviceProperties");
    fprintf(stderr, "GPU stress on %s (compute %d.%d), iterations=%d\n",
            prop.name, prop.major, prop.minor, iterations);

    const int n = 1 << 22;
    const size_t bytes = static_cast<size_t>(n) * sizeof(float);
    float* d_x = nullptr;
    float* d_y = nullptr;
    check_cuda(cudaMalloc(&d_x, bytes), "cudaMalloc x");
    check_cuda(cudaMalloc(&d_y, bytes), "cudaMalloc y");
    check_cuda(cudaMemset(d_x, 1, bytes), "cudaMemset x");
    check_cuda(cudaMemset(d_y, 0, bytes), "cudaMemset y");

    const int threads = 256;
    const int blocks = (n + threads - 1) / threads;

    while (iterations-- > 0) {
        saxpy_kernel<<<blocks, threads>>>(n, 2.0f, d_x, d_y);
        check_cuda(cudaGetLastError(), "kernel launch");
    }
    check_cuda(cudaDeviceSynchronize(), "cudaDeviceSynchronize");

    cudaFree(d_x);
    cudaFree(d_y);
    return 0;
}
