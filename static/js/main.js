document.addEventListener('DOMContentLoaded', function () {
    // 文件选择
    const fileInput = document.getElementById('fileInput');
    const selectFileBtn = document.getElementById('selectFileBtn');
    const uploadForm = document.getElementById('uploadForm');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const uploadBtn = document.getElementById('uploadBtn');

    // 显示消息函数
    function showMessage(message, type) {
        // 创建消息元素
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${type}`;
        messageEl.textContent = message;
        
        // 添加样式
        messageEl.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 4px;
            color: white;
            font-weight: 500;
            z-index: 1000;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transform: translateX(100%);
            transition: transform 0.3s ease;
            ${type === 'success' ? 'background-color: #4CAF50;' : 'background-color: #f44336;'}
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

    // 在页面加载时获取配置
    let fileSizeLimit = 10; // 默认值
    // 从后端获取上传文件大小限制
    fetch('/api/config')
        .then(response => response.json())
        .then(data => {
            if (data.file_size_limit) {
                fileSizeLimit = data.file_size_limit;
            }
        })
        .catch(error => {
            console.error('Failed to load config:', error);
        });

    if (selectFileBtn) {
        selectFileBtn.addEventListener('click', function () {
            fileInput.click();
        });
    }

    if (fileInput) {
        fileInput.addEventListener('change', function () {
            if (fileInput.files.length > 0) {
                const file = fileInput.files[0];
                displayFileInfo(file);
            }
        });
    }

    // 拖放功能
    const dropArea = document.querySelector('.file-select');
    if (dropArea) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            dropArea.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropArea.addEventListener(eventName, unhighlight, false);
        });

        function highlight() {
            dropArea.classList.add('highlight');
        }

        function unhighlight() {
            dropArea.classList.remove('highlight');
        }

        dropArea.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const file = dt.files[0];

            if (file) {
                fileInput.files = dt.files;
                displayFileInfo(file);
            }
        }
    }

    function displayFileInfo(file) {
        fileName.textContent = file.name;

        // 格式化文件大小
        const fileSizeMB = file.size / (1024 * 1024);
        fileSize.textContent = fileSizeMB.toFixed(2) + ' MiB';

        // 显示上传表单
        uploadForm.style.display = 'block';

        // 检查文件大小
        if (fileSizeMB > fileSizeLimit) {
            showMessage('File size over the ' + fileSizeLimit + ' MiB limit!', 'error');
            uploadBtn.disabled = true;
            uploadBtn.classList.add('disabled-btn');  // 添加禁用样式
        } else {
            uploadBtn.disabled = false;
            uploadBtn.classList.remove('disabled-btn');  // 移除禁用样式
        }
    }

    // 文件上传 - 使用分片上传
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function () {
            if (!fileInput.files.length) return;

            const file = fileInput.files[0];
            
            // 获取过期选项
            const expiryOptions = document.getElementsByName('expiry');
            let selectedExpiry = '1 day';

            for (const option of expiryOptions) {
                if (option.checked) {
                    selectedExpiry = option.value;
                    break;
                }
            }

            // 显示上传中状态
            uploadBtn.textContent = 'uploading...';
            uploadBtn.disabled = true;

            // 创建分片上传器
            const chunkUploader = new ChunkUploader({
                chunkSize: 2 * 1024 * 1024, // 2MB chunks
                maxConcurrent: 3,
                maxRetries: 3,
                retryDelay: 1000,
                onProgress: function(progress) {
                    // 更新上传进度
                    const percent = Math.round(progress.progress);
                    uploadBtn.textContent = `uploading... ${percent}%`;
                },
                onSuccess: function(result) {
                    // 上传成功
                    showMessage('Upload completed successfully!', 'success');
                    // 重定向到文件页面
                    window.location.href = `/upload?file_hash=${result.file_hash}`;
                },
                onError: function(error) {
                    // 上传失败
                    console.error('Upload error:', error);
                    showMessage('Upload failed: ' + error.message, 'error');
                    uploadBtn.textContent = 'Encrypt and upload';
                    uploadBtn.disabled = false;
                },
                onPause: function() {
                    uploadBtn.textContent = 'Upload paused';
                },
                onResume: function() {
                    uploadBtn.textContent = 'uploading...';
                },
                onCancel: function() {
                    uploadBtn.textContent = 'Encrypt and upload';
                    uploadBtn.disabled = false;
                }
            });

            // 开始分片上传
            chunkUploader.uploadFile(file, selectedExpiry);
        });
    }

    // 获取当前页面的域名和协议
    const baseUrl = window.location.origin;

    // 设置复制按钮的数据
    const publicLinkBtn = document.getElementById('copy-public-btn');
    const protectedLinkBtn = document.getElementById('copy-protected-btn');
    const publicLinkInput = document.getElementById('public-link');
    const protectedLinkInput = document.getElementById('protected-link');

    // 更新输入框显示完整URL（添加条件检查）
    if (publicLinkInput) {
        publicLinkInput.value = baseUrl + publicLinkInput.value;
    }
    if (protectedLinkInput) {
        protectedLinkInput.value = baseUrl + protectedLinkInput.value;
    }

    // 设置复制按钮点击事件
    if (publicLinkBtn) {
        publicLinkBtn.addEventListener('click', function () {
            navigator.clipboard.writeText(publicLinkInput.value)
                .then(() => {
                    const originalText = this.querySelector('span:last-child').textContent;
                    this.querySelector('span:last-child').textContent = 'Copying!';

                    setTimeout(() => {
                        this.querySelector('span:last-child').textContent = originalText;
                    }, 2000);
                })
                .catch(err => {
                    console.error('copy failed:', err);
                });
        });
    }

    if (protectedLinkBtn) {
        protectedLinkBtn.addEventListener('click', function () {
            navigator.clipboard.writeText(protectedLinkInput.value)
                .then(() => {
                    const originalText = this.querySelector('span:last-child').textContent;
                    this.querySelector('span:last-child').textContent = 'Copying!';

                    setTimeout(() => {
                        this.querySelector('span:last-child').textContent = originalText;
                    }, 2000);
                })
                .catch(err => {
                    console.error('copy failed:', err);
                });
        });
    }

    // 为下载链接添加分片下载功能
    const downloadLinks = document.querySelectorAll('a[href*="/file?hash="]');
    downloadLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const url = new URL(this.href);
            const fileHash = url.searchParams.get('hash');
            const password = url.searchParams.get('pwd');
            
            if (!fileHash) return;
            
            console.log('Starting chunk download for file:', fileHash);
            
            // 创建下载进度显示元素
            const progressContainer = document.createElement('div');
            progressContainer.className = 'download-progress';
            progressContainer.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: white;
                border: 1px solid #ccc;
                border-radius: 2px;
                padding: 10px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                z-index: 1000;
                min-width: 300px;
            `;
            
            progressContainer.innerHTML = `
                <h3>下载进度</h3>
                <div class="progress-bar" style="width: 100%; height: 20px; background: #f0f0f0; border-radius: 2px; overflow: hidden; margin: 10px 0;">
                    <div class="progress-fill" style="width: 0%; height: 100%; background:rgb(233, 93, 114); transition: width 0.3s;"></div>
                </div>
                <div class="progress-text" style="text-align: center; margin: 10px 0;">0%</div>
            `;
            
            document.body.appendChild(progressContainer);
            
            const progressFill = progressContainer.querySelector('.progress-fill');
            const progressText = progressContainer.querySelector('.progress-text');
            
            // 对于大文件，使用分片下载
            const chunkDownloader = new ChunkDownloader({
                chunkSize: 1024 * 1024, // 1MB chunks
                maxConcurrent: 3,
                maxRetries: 3,
                retryDelay: 1000,
                onProgress: function(progress) {
                    console.log(`Download progress: ${Math.round(progress.progress)}%`);
                    progressFill.style.width = progress.progress + '%';
                    progressText.textContent = `${Math.round(progress.progress)}%`;
                },
                onSuccess: function(result) {
                    console.log('Download completed successfully:', result);
                    progressContainer.remove();
                    // 创建下载链接并触发下载
                    chunkDownloader.createDownloadLink(result.blob, result.fileName);
                },
                onError: function(error) {
                    console.error('Download error:', error);
                    progressContainer.remove();
                    // 如果分片下载失败，回退到普通下载
                    console.log('Falling back to normal download');
                    window.open(link.href, '_blank');
                }
            });
            
            // 开始分片下载
            chunkDownloader.downloadFile(fileHash, password);
        });
    });


});