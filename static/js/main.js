document.addEventListener('DOMContentLoaded', function () {
    // 文件选择
    const fileInput = document.getElementById('fileInput');
    const selectFileBtn = document.getElementById('selectFileBtn');
    const uploadForm = document.getElementById('uploadForm');
    const fileName = document.getElementById('fileName');
    const fileSize = document.getElementById('fileSize');
    const uploadBtn = document.getElementById('uploadBtn');

    // 在页面加载时获取配置
    let fileSizeLimit = 10; // 默认值

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
            alert('File size over the ' + fileSizeLimit + ' MiB limit!');
            uploadBtn.disabled = true;
            uploadBtn.classList.add('disabled-btn');  // 添加禁用样式
        } else {
            uploadBtn.disabled = false;
            uploadBtn.classList.remove('disabled-btn');  // 移除禁用样式
        }
    }

    // 文件上传
    if (uploadBtn) {
        uploadBtn.addEventListener('click', function () {
            if (!fileInput.files.length) return;

            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('file', file);

            // 获取过期选项
            const expiryOptions = document.getElementsByName('expiry');
            let selectedExpiry = '1 day';

            for (const option of expiryOptions) {
                if (option.checked) {
                    selectedExpiry = option.value;
                    break;
                }
            }

            formData.append('expiry', selectedExpiry);
            formData.append('file_name', file.name);

            // 显示上传中状态
            uploadBtn.textContent = 'uploading...';
            uploadBtn.disabled = true;

            // 发送上传请求
            fetch('/upload', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // 将完整的文件信息编码后传递给upload路由
                        const fileInfoEncoded = encodeURIComponent(JSON.stringify(data));
                        // 重定向到文件页面
                        window.location.href = `/upload?file_info=${fileInfoEncoded}`;
                    } else {
                        alert('upload failed: ' + data.message);
                        uploadBtn.textContent = 'Encrypt and upload';
                        uploadBtn.disabled = false;
                    }
                })
                .catch(error => {
                    console.error('upload error:', error);
                    alert('There was an error in uploading. Please try again.');
                    uploadBtn.textContent = 'Encrypt and upload';
                    uploadBtn.disabled = false;
                });
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