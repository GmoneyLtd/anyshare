class ChunkDownloader {
    constructor(options = {}) {
        this.chunkSize = options.chunkSize || 1024 * 1024; // 1MB default
        this.maxConcurrent = options.maxConcurrent || 3; // 最大并发数
        this.maxRetries = options.maxRetries || 3; // 最大重试次数
        this.retryDelay = options.retryDelay || 1000; // 重试延迟(ms)

        this.fileHash = null;
        this.password = null;
        this.fileSize = 0;
        this.totalChunks = 0;
        this.downloadedChunks = new Set();
        this.failedChunks = new Set();
        this.isDownloading = false;
        this.isPaused = false;
        this.isCancelled = false;
        this.chunks = new Map(); // 存储下载的分片数据

        // 回调函数
        this.onProgress = options.onProgress || (() => { });
        this.onSuccess = options.onSuccess || (() => { });
        this.onError = options.onError || (() => { });
        this.onPause = options.onPause || (() => { });
        this.onResume = options.onResume || (() => { });
        this.onCancel = options.onCancel || (() => { });
    }

    async downloadFile(fileHash, password) {
        this.fileHash = fileHash;
        this.password = password;
        this.isDownloading = true;
        this.isPaused = false;
        this.isCancelled = false;

        console.log('ChunkDownloader: Starting download for file:', fileHash);

        try {
            // 获取文件信息
            const fileInfo = await this.getFileInfo();
            if (fileInfo.status !== 'success') {
                throw new Error(fileInfo.message || 'Failed to get file info');
            }

            this.fileSize = fileInfo.file_size;
            this.totalChunks = Math.ceil(this.fileSize / this.chunkSize);

            console.log(`ChunkDownloader: File size: ${this.fileSize}, Total chunks: ${this.totalChunks}`);

            // 检查是否有已下载的分片（断点续传）
            this.loadDownloadProgress();

            // 开始分片下载
            await this.downloadChunks();

            // 合并文件
            const blob = await this.mergeChunks();
            
            console.log('ChunkDownloader: Download completed, blob size:', blob.size);
            
            // 清除下载进度
            this.clearDownloadProgress();
            
            // 更新下载次数（只在完整下载完成时）
            await this.updateDownloadCount();
            
            // 触发成功回调
            this.onSuccess({
                blob: blob,
                fileName: fileInfo.file_name,
                fileSize: this.fileSize
            });

        } catch (error) {
            console.error('ChunkDownloader: Download failed:', error);
            this.isDownloading = false;
            this.onError(error);
        }
    }

    // 更新下载次数
    async updateDownloadCount() {
        try {
            const url = `/file?hash=${this.fileHash}&pwd=${this.password}`;
            const response = await fetch(url, { 
                method: 'GET',
                headers: {
                    'X-Update-Download-Count': 'true'
                }
            });
            
            if (response.ok) {
                console.log('ChunkDownloader: Download count updated');
            }
        } catch (error) {
            console.error('ChunkDownloader: Failed to update download count:', error);
        }
    }

    // 保存下载进度到localStorage
    saveDownloadProgress() {
        const progress = {
            fileHash: this.fileHash,
            fileSize: this.fileSize,
            totalChunks: this.totalChunks,
            downloadedChunks: Array.from(this.downloadedChunks),
            timestamp: Date.now()
        };
        localStorage.setItem(`download_progress_${this.fileHash}`, JSON.stringify(progress));
    }

    // 从localStorage加载下载进度
    loadDownloadProgress() {
        const progressKey = `download_progress_${this.fileHash}`;
        const progressData = localStorage.getItem(progressKey);
        
        if (progressData) {
            try {
                const progress = JSON.parse(progressData);
                // 检查进度是否仍然有效（24小时内）
                if (Date.now() - progress.timestamp < 24 * 60 * 60 * 1000) {
                    this.downloadedChunks = new Set(progress.downloadedChunks);
                    console.log(`ChunkDownloader: Resumed download with ${this.downloadedChunks.size} chunks already downloaded`);
                } else {
                    // 清除过期的进度
                    localStorage.removeItem(progressKey);
                }
            } catch (error) {
                console.error('ChunkDownloader: Failed to load download progress:', error);
                localStorage.removeItem(progressKey);
            }
        }
    }

    // 清除下载进度
    clearDownloadProgress() {
        const progressKey = `download_progress_${this.fileHash}`;
        localStorage.removeItem(progressKey);
    }

    async getFileInfo() {
        const url = `/file?hash=${this.fileHash}&pwd=${this.password}`;
        console.log('ChunkDownloader: Getting file info from:', url);
        
        const response = await fetch(url, { method: 'HEAD' });
        
        if (response.ok) {
            const contentLength = response.headers.get('Content-Length');
            const contentDisposition = response.headers.get('Content-Disposition');
            
            console.log('ChunkDownloader: Response headers:', {
                'Content-Length': contentLength,
                'Content-Disposition': contentDisposition
            });
            
            // 从Content-Disposition中提取文件名
            let fileName = 'download';
            if (contentDisposition) {
                const match = contentDisposition.match(/filename="([^"]+)"/);
                if (match) {
                    fileName = match[1];
                }
            }

            return {
                status: 'success',
                file_size: parseInt(contentLength) || 0,
                file_name: fileName
            };
        } else {
            console.error('ChunkDownloader: Failed to get file info:', response.status, response.statusText);
            return {
                status: 'error',
                message: `HTTP ${response.status}: ${response.statusText}`
            };
        }
    }

    async downloadChunks() {
        const pendingChunks = [];

        // 创建待下载分片列表
        for (let i = 0; i < this.totalChunks; i++) {
            if (!this.downloadedChunks.has(i)) {
                pendingChunks.push(i);
            }
        }

        // 并发下载分片
        const downloadPromises = [];
        let currentIndex = 0;

        const downloadNext = async () => {
            while (currentIndex < pendingChunks.length && !this.isPaused && !this.isCancelled) {
                if (downloadPromises.length >= this.maxConcurrent) {
                    // 等待一个下载完成
                    await Promise.race(downloadPromises);
                    continue;
                }

                const chunkIndex = pendingChunks[currentIndex++];
                const promise = this.downloadChunk(chunkIndex)
                    .then(() => {
                        // 从promises数组中移除
                        const index = downloadPromises.indexOf(promise);
                        if (index > -1) {
                            downloadPromises.splice(index, 1);
                        }
                    })
                    .catch(error => {
                        // 从promises数组中移除
                        const index = downloadPromises.indexOf(promise);
                        if (index > -1) {
                            downloadPromises.splice(index, 1);
                        }
                        throw error;
                    });

                downloadPromises.push(promise);
            }

            // 等待所有下载完成
            await Promise.all(downloadPromises);
        };

        await downloadNext();

        // 检查是否有失败的分片需要重试
        if (this.failedChunks.size > 0 && !this.isPaused && !this.isCancelled) {
            throw new Error(`Failed to download ${this.failedChunks.size} chunks`);
        }
    }

    async downloadChunk(chunkIndex, retryCount = 0) {
        if (this.isPaused || this.isCancelled) {
            return;
        }

        try {
            const start = chunkIndex * this.chunkSize;
            const end = Math.min(start + this.chunkSize - 1, this.fileSize - 1);

            console.log(`Downloading chunk ${chunkIndex}: bytes ${start}-${end}`);

            const url = `/file?hash=${this.fileHash}&pwd=${this.password}`;
            const response = await fetch(url, {
                headers: {
                    'Range': `bytes=${start}-${end}`
                }
            });

            if (response.ok) {
                const chunkData = await response.arrayBuffer();
                this.chunks.set(chunkIndex, chunkData);
                this.downloadedChunks.add(chunkIndex);
                this.failedChunks.delete(chunkIndex);

                console.log(`Chunk ${chunkIndex} downloaded successfully: ${chunkData.byteLength} bytes`);

                // 保存下载进度（断点续传）
                this.saveDownloadProgress();

                // 更新进度
                const progress = (this.downloadedChunks.size / this.totalChunks) * 100;
                this.onProgress({
                    progress: progress,
                    downloadedChunks: this.downloadedChunks.size,
                    totalChunks: this.totalChunks,
                    chunkIndex: chunkIndex
                });

            } else {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

        } catch (error) {
            console.error(`Failed to download chunk ${chunkIndex}:`, error);
            this.failedChunks.add(chunkIndex);

            // 重试逻辑
            if (retryCount < this.maxRetries) {
                console.log(`Retrying chunk ${chunkIndex}, attempt ${retryCount + 1}`);
                await this.delay(this.retryDelay * (retryCount + 1));
                return this.downloadChunk(chunkIndex, retryCount + 1);
            } else {
                throw error;
            }
        }
    }

    async mergeChunks() {
        // 按顺序合并分片
        const chunks = [];
        for (let i = 0; i < this.totalChunks; i++) {
            const chunkData = this.chunks.get(i);
            if (chunkData) {
                chunks.push(new Uint8Array(chunkData));
            }
        }

        // 创建Blob
        return new Blob(chunks, { type: 'application/octet-stream' });
    }

    async pause() {
        this.isPaused = true;
        console.log('ChunkDownloader: Download paused');
        this.onPause();
    }

    async resume() {
        if (!this.isPaused || this.isCancelled) {
            return;
        }

        this.isPaused = false;
        console.log('ChunkDownloader: Download resumed');
        this.onResume();

        try {
            // 继续下载剩余分片
            await this.downloadChunks();

            // 合并文件
            const blob = await this.mergeChunks();
            
            // 清除下载进度
            this.clearDownloadProgress();
            
            // 触发成功回调
            this.onSuccess({
                blob: blob,
                fileName: this.fileName,
                fileSize: this.fileSize
            });

        } catch (error) {
            this.onError(error);
        }
    }

    async cancel() {
        this.isCancelled = true;
        this.isDownloading = false;
        this.chunks.clear();
        console.log('ChunkDownloader: Download cancelled');
        this.onCancel();
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // 创建下载链接并触发下载
    createDownloadLink(blob, fileName) {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = fileName;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
}

// 导出到全局
window.ChunkDownloader = ChunkDownloader;
