document.addEventListener('DOMContentLoaded', function () {
    // 文件选择
    const fileInput = document.getElementById('fileInput');
    const selectFileBtn = document.getElementById('selectFileBtn');
    const uploadForm = document.getElementById('uploadForm');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const uploadBtn = document.getElementById('uploadBtn');

    // 生成随机密码的函数
    function generatePassword() {
        const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        let password = '';
        for (let i = 0; i < 6; i++) {
            password += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        return password;
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

            // 生成密码
            const password = generatePassword();

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
                    // 重定向到文件页面，包含文件哈希和密码
                    if (result.file_hash) {
                        window.location.href = `/upload?hash=${result.file_hash}&pwd=${password}`;
                    } else {
                        // 如果没有文件哈希信息，仍然重定向到文件页面（会要求输入密码）
                        window.location.href = `/upload`;
                    }
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
            chunkUploader.uploadFile(file, selectedExpiry, password);
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
});