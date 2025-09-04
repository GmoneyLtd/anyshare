class ChunkUploader {
    constructor(options = {}) {
        this.chunkSize = options.chunkSize || 2 * 1024 * 1024; // 2MB default
        this.maxConcurrent = options.maxConcurrent || 3; // 最大并发数
        this.maxRetries = options.maxRetries || 3; // 最大重试次数
        this.retryDelay = options.retryDelay || 1000; // 重试延迟(ms)

        this.file = null;
        this.sessionId = null;
        this.totalChunks = 0;
        this.uploadedChunks = new Set();
        this.failedChunks = new Set();
        this.isUploading = false;
        this.isPaused = false;
        this.isCancelled = false;

        // 回调函数
        this.onProgress = options.onProgress || (() => { });
        this.onSuccess = options.onSuccess || (() => { });
        this.onError = options.onError || (() => { });
        this.onPause = options.onPause || (() => { });
        this.onResume = options.onResume || (() => { });
        this.onCancel = options.onCancel || (() => { });
    }

    async uploadFile(file, expiryOption = '1 day', password = null) {
        this.file = file;
        this.expiryOption = expiryOption;
        this.password = password;
        this.totalChunks = Math.ceil(file.size / this.chunkSize);
        this.uploadedChunks.clear();
        this.failedChunks.clear();
        this.isUploading = true;
        this.isPaused = false;
        this.isCancelled = false;

        try {
            // 创建上传会话
            const sessionResult = await this.createSession();
            if (sessionResult.status !== 'success') {
                throw new Error(sessionResult.message || 'Failed to create upload session');
            }

            this.sessionId = sessionResult.session_id;
            this.totalChunks = sessionResult.total_chunks;

            // 检查是否有已上传的分片(断点续传)
            if (sessionResult.uploaded_chunks && sessionResult.uploaded_chunks.length > 0) {
                sessionResult.uploaded_chunks.forEach(index => {
                    this.uploadedChunks.add(index);
                });
            }

            // 开始上传分片
            await this.uploadChunks();

            // 完成上传
            const completeResult = await this.completeUpload();
            if (completeResult.status === 'success') {
                // 将密码添加到结果中
                if (this.password) {
                    completeResult.password = this.password;
                }
                this.onSuccess(completeResult);
            } else {
                throw new Error(completeResult.message || 'Failed to complete upload');
            }

        } catch (error) {
            this.isUploading = false;
            this.onError(error);
        }
    }

    async createSession() {
        const formData = new FormData();
        formData.append('file_name', this.file.name);
        formData.append('file_size', this.file.size.toString());
        formData.append('chunk_size', this.chunkSize.toString());

        const response = await fetch('/api/chunk/session', {
            method: 'POST',
            body: formData
        });

        return await response.json();
    }

    async uploadChunks() {
        const pendingChunks = [];

        // 创建待上传分片列表
        for (let i = 0; i < this.totalChunks; i++) {
            if (!this.uploadedChunks.has(i)) {
                pendingChunks.push(i);
            }
        }

        // 并发上传分片
        const uploadPromises = [];
        let currentIndex = 0;

        const uploadNext = async () => {
            while (currentIndex < pendingChunks.length && !this.isPaused && !this.isCancelled) {
                if (uploadPromises.length >= this.maxConcurrent) {
                    // 等待一个上传完成
                    await Promise.race(uploadPromises);
                    continue;
                }

                const chunkIndex = pendingChunks[currentIndex++];
                const promise = this.uploadChunk(chunkIndex)
                    .then(() => {
                        // 从promises数组中移除
                        const index = uploadPromises.indexOf(promise);
                        if (index > -1) {
                            uploadPromises.splice(index, 1);
                        }
                    })
                    .catch(error => {
                        // 从promises数组中移除
                        const index = uploadPromises.indexOf(promise);
                        if (index > -1) {
                            uploadPromises.splice(index, 1);
                        }
                        throw error;
                    });

                uploadPromises.push(promise);
            }

            // 等待所有上传完成
            await Promise.all(uploadPromises);
        };

        await uploadNext();

        // 检查是否有失败的分片需要重试
        if (this.failedChunks.size > 0 && !this.isPaused && !this.isCancelled) {
            throw new Error(`Failed to upload ${this.failedChunks.size} chunks`);
        }
    }

    async uploadChunk(chunkIndex, retryCount = 0) {
        if (this.isPaused || this.isCancelled) {
            return;
        }

        try {
            const start = chunkIndex * this.chunkSize;
            const end = Math.min(start + this.chunkSize, this.file.size);
            const chunk = this.file.slice(start, end);

            const formData = new FormData();
            formData.append('session_id', this.sessionId);
            formData.append('chunk_index', chunkIndex.toString());
            formData.append('chunk', chunk);

            const response = await fetch('/api/chunk/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (result.status === 'success') {
                this.uploadedChunks.add(chunkIndex);
                this.failedChunks.delete(chunkIndex);

                // 更新进度
                const progress = (this.uploadedChunks.size / this.totalChunks) * 100;
                this.onProgress({
                    progress: progress,
                    uploadedChunks: this.uploadedChunks.size,
                    totalChunks: this.totalChunks,
                    chunkIndex: chunkIndex
                });

            } else {
                throw new Error(result.message || 'Upload chunk failed');
            }

        } catch (error) {
            this.failedChunks.add(chunkIndex);

            // 重试逻辑
            if (retryCount < this.maxRetries) {
                await this.delay(this.retryDelay * (retryCount + 1));
                return this.uploadChunk(chunkIndex, retryCount + 1);
            } else {
                throw error;
            }
        }
    }

    async completeUpload() {
        const formData = new FormData();
        formData.append('session_id', this.sessionId);
        formData.append('expiry_option', this.expiryOption);
        // 如果有密码，也传递给后端
        if (this.password) {
            formData.append('password', this.password);
        }

        const response = await fetch('/api/chunk/complete', {
            method: 'POST',
            body: formData
        });

        return await response.json();
    }

    async pause() {
        this.isPaused = true;
        this.onPause();
    }

    async resume() {
        if (!this.isPaused || this.isCancelled) {
            return;
        }

        this.isPaused = false;
        this.onResume();

        try {
            // 继续上传剩余分片
            await this.uploadChunks();

            // 完成上传
            const completeResult = await this.completeUpload();
            if (completeResult.status === 'success') {
                this.onSuccess(completeResult);
            } else {
                throw new Error(completeResult.message || 'Failed to complete upload');
            }

        } catch (error) {
            this.onError(error);
        }
    }

    async cancel() {
        this.isCancelled = true;
        this.isUploading = false;

        if (this.sessionId) {
            try {
                const formData = new FormData();
                formData.append('session_id', this.sessionId);

                await fetch('/api/chunk/cancel', {
                    method: 'POST',
                    body: formData
                });
            } catch (error) {
                console.error('Failed to cancel upload session:', error);
            }
        }

        this.onCancel();
    }

    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// 导出到全局
window.ChunkUploader = ChunkUploader;