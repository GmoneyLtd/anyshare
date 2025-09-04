class ChunkDownloader {
    constructor(options = {}) {
        this.chunkSize = options.chunkSize || 2 * 1024 * 1024; // 默认2MB
        this.maxConcurrent = options.maxConcurrent || 3;
        this.maxRetries = options.maxRetries || 3;
        this.retryDelay = options.retryDelay || 1000;
        this.onProgress = options.onProgress || (() => {});
        this.onSuccess = options.onSuccess || (() => {});
        this.onError = options.onError || (() => {});
    }

    async downloadFile(url, filename) {
        try {
            // 获取文件大小
            const headResponse = await fetch(url, { method: 'HEAD' });
            const contentLength = headResponse.headers.get('Content-Length');
            
            if (!contentLength) {
                throw new Error('无法获取文件大小');
            }
            
            const fileSize = parseInt(contentLength, 10);
            console.log(`文件大小: ${fileSize} bytes`);
            
            // 创建用于存储文件块的数组
            const chunks = new Array(Math.ceil(fileSize / this.chunkSize));
            let downloadedBytes = 0;
            
            // 创建下载任务
            const tasks = [];
            for (let start = 0; start < fileSize; start += this.chunkSize) {
                const end = Math.min(start + this.chunkSize - 1, fileSize - 1);
                const chunkIndex = Math.floor(start / this.chunkSize);
                tasks.push({ start, end, chunkIndex });
            }
            
            // 并发下载文件块
            await this._downloadChunksConcurrently(url, tasks, chunks, fileSize, (bytes) => {
                downloadedBytes += bytes;
                const progress = (downloadedBytes / fileSize) * 100;
                this.onProgress({
                    progress: progress,
                    downloaded: downloadedBytes,
                    total: fileSize
                });
            });
            
            // 合并文件块
            const blob = new Blob(chunks);
            this._saveFile(blob, filename);
            
            this.onSuccess({
                url: url,
                filename: filename,
                size: fileSize
            });
        } catch (error) {
            console.error('下载失败:', error);
            this.onError(error);
        }
    }

    async _downloadChunksConcurrently(url, tasks, chunks, fileSize, onChunkDownloaded) {
        const semaphore = new Semaphore(this.maxConcurrent);
        
        const downloadPromises = tasks.map(task => 
            semaphore.acquire().then(async () => {
                try {
                    const chunk = await this._downloadChunk(url, task.start, task.end, this.maxRetries);
                    chunks[task.chunkIndex] = chunk;
                    onChunkDownloaded(chunk.size);
                } finally {
                    semaphore.release();
                }
            })
        );
        
        await Promise.all(downloadPromises);
    }

    async _downloadChunk(url, start, end, retries) {
        for (let i = 0; i <= retries; i++) {
            try {
                const response = await fetch(url, {
                    headers: {
                        'Range': `bytes=${start}-${end}`
                    }
                });
                
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                
                return await response.blob();
            } catch (error) {
                if (i === retries) {
                    throw error;
                }
                
                console.warn(`下载块 ${start}-${end} 失败，${this.retryDelay}ms 后重试... (${i + 1}/${retries})`);
                await new Promise(resolve => setTimeout(resolve, this.retryDelay));
            }
        }
    }

    _saveFile(blob, filename) {
        // 创建下载链接
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename || 'download';
        
        // 触发下载
        document.body.appendChild(a);
        a.click();
        
        // 清理
        setTimeout(() => {
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }, 100);
    }
}

// 信号量实现，用于控制并发数
class Semaphore {
    constructor(max) {
        this.max = max;
        this.current = 0;
        this.queue = [];
    }

    async acquire() {
        return new Promise((resolve) => {
            if (this.current < this.max) {
                this.current++;
                resolve();
            } else {
                this.queue.push(resolve);
            }
        });
    }

    release() {
        this.current--;
        if (this.queue.length > 0) {
            this.current++;
            const resolve = this.queue.shift();
            resolve();
        }
    }
}

// 页面加载完成后初始化分片下载功能
document.addEventListener('DOMContentLoaded', function () {
    // 获取分片下载按钮
    const chunkedDownloadBtn = document.getElementById('chunked-download-btn');
    
    if (chunkedDownloadBtn) {
        chunkedDownloadBtn.addEventListener('click', function () {
            // 获取当前页面的URL
            const url = window.location.href;
            
            // 从URL中提取文件哈希
            const urlParams = new URLSearchParams(window.location.search);
            const fileHash = urlParams.get('hash');
            
            if (!fileHash) {
                console.error('无法获取文件哈希');
                showMessage('无法获取文件信息', 'error');
                return;
            }
            
            // 先获取文件信息
            fetch(`/api/file/${fileHash}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // 创建分片下载器
                        const chunkDownloader = new ChunkDownloader({
                            chunkSize: 2 * 1024 * 1024, // 2MB chunks
                            maxConcurrent: 3,
                            maxRetries: 3,
                            retryDelay: 1000,
                            onProgress: function(progress) {
                                // 更新下载进度
                                console.log(`下载进度: ${Math.round(progress.progress)}%`);
                            },
                            onSuccess: function(result) {
                                // 下载成功
                                console.log('下载完成:', result);
                                showMessage('Download completed successfully!', 'success');
                            },
                            onError: function(error) {
                                // 下载失败
                                console.error('下载失败:', error);
                                showMessage('Download failed: ' + error.message, 'error');
                            }
                        });

                        // 使用原始文件名
                        const filename = data.file_name || fileHash || 'download';

                        // 开始分片下载
                        chunkDownloader.downloadFile(url, filename);
                    } else {
                        console.error('获取文件信息失败:', data.message);
                        showMessage('Failed to get file info: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('获取文件信息失败:', error);
                    showMessage('Failed to get file info', 'error');
                });
        });
    }
    
    // 显示消息函数
    function showMessage(message, type) {
        // 创建消息元素
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.textContent = message;

        // 添加样式
        messageEl.style.cssText = `
            position: fixed;
            top: 100px;
            right: 5px;
            padding: 5px 10px;
            border-radius: 4px;
            color: white;
            font-weight: 400;
            font-size: 10.5px;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transform: translateX(100%);
            transition: transform 0.3s ease;
            ${type === 'success' ? 'background-color:rgb(237, 142, 161);' : 'background-color:rgba(123, 103, 102, 0.63);'}
        `;

        // 添加到页面
        document.body.appendChild(messageEl);

        // 显示动画
        setTimeout(() => {
            messageEl.style.transform = 'translateX(0)';
        }, 10);

        // 3秒后自动移除
        setTimeout(() => {
            messageEl.style.transform = 'translateX(100%)';
            setTimeout(() => {
                document.body.removeChild(messageEl);
            }, 300);
        }, 3000);
    }
});