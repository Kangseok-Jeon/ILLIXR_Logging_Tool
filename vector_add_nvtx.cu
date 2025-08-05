#include <stdio.h>
#include <nvToolsExt.h>
#include <cuda_runtime.h>

__global__ void add(int *a, int *b, int *c) {
    int tid = threadIdx.x;
    c[tid] = a[tid] + b[tid];
}

int main() {
    const int N = 5;
    int ha[N] = {1,2,3,4,5}, hb[N] = {10,20,30,40,50}, hc[N];
    int *da, *db, *dc;

    // -------------------- Malloc --------------------
    nvtxRangePushA("cudaMalloc1");
    cudaMalloc((void**)&da, N * sizeof(int));
    nvtxRangePop();
    
    nvtxRangePushA("cudaMalloc2");
    cudaMalloc((void**)&db, N * sizeof(int));
    nvtxRangePop();

    nvtxRangePushA("cudaMalloc3");
    cudaMalloc((void**)&dc, N * sizeof(int));
    nvtxRangePop();

    // -------------------- H2D Memcpy --------------------
    nvtxRangePushA("H2D memcpy");
    cudaMemcpy(da, ha, N * sizeof(int), cudaMemcpyHostToDevice);
    cudaMemcpy(db, hb, N * sizeof(int), cudaMemcpyHostToDevice);
    nvtxRangePop();

    // -------------------- Kernel --------------------
    nvtxRangePushA("Kernel launch");
    add<<<1, N>>>(da, db, dc);
    cudaDeviceSynchronize();  // 커널 실행 기다림
    nvtxRangePop();

    // -------------------- D2H Memcpy --------------------
    nvtxRangePushA("D2H memcpy");
    cudaMemcpy(hc, dc, N * sizeof(int), cudaMemcpyDeviceToHost);
    nvtxRangePop();

    // -------------------- 결과 출력 --------------------
    for (int i = 0; i < N; i++)
        printf("%d + %d = %d\n", ha[i], hb[i], hc[i]);

    // -------------------- Free --------------------
    nvtxRangePushA("cudaFree");
    cudaFree(da);
    cudaFree(db);
    cudaFree(dc);
    nvtxRangePop();

    return 0;
}

