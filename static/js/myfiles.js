document.addEventListener('DOMContentLoaded', function () {
    // 时区转换功能
    const timeElements = document.querySelectorAll('[data-utc-time]');
    timeElements.forEach(element => {
        const utcTimeStr = element.getAttribute('data-utc-time');
        if (utcTimeStr) {
            try {
                const utcDate = new Date(utcTimeStr);
                const options = {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                    year: 'numeric',
                    hour12: false
                };
                const dateParts = utcDate.toLocaleString('en-US', options).split(', ');
                const localTimeStr = `${dateParts[0]} ${dateParts[1]} ${dateParts[2]}`;
                element.textContent = `(${localTimeStr})`;
            } catch (e) {
                console.error('时间转换错误:', e);
            }
        }
    });

    // 为文件名添加悬停显示完整内容的功能
    function addFileNameHoverEffect() {
        // 查找所有文件名容器（包括表格和卡片中的）
        const fileNameContainers = document.querySelectorAll('.file-name-container');
        let globalPopupElement = null;
        let globalRemoveTimer = null;
        let globalShowTimer = null;
        let activeElement = null;

        fileNameContainers.forEach(container => {
            const element = container.querySelector('.file-name');
            if (element && element.scrollWidth > element.offsetWidth) {
                element.addEventListener('mouseenter', function (e) {
                    activeElement = element;
                    if (globalRemoveTimer) {
                        clearTimeout(globalRemoveTimer);
                        globalRemoveTimer = null;
                    }
                    globalShowTimer = setTimeout(() => {
                        removeAllFileNamePopups();
                        globalPopupElement = document.createElement('div');
                        globalPopupElement.className = 'file-name full-name-popup';
                        globalPopupElement.textContent = element.textContent;
                        updatePopupPosition(e, globalPopupElement);
                        document.body.appendChild(globalPopupElement);
                    }, 500);
                });

                let lastMoveTime = 0;
                element.addEventListener('mousemove', function (e) {
                    if (globalPopupElement && element === activeElement) {
                        const now = Date.now();
                        if (now - lastMoveTime > 50) {
                            lastMoveTime = now;
                            updatePopupPosition(e, globalPopupElement);
                        }
                    }
                });

                element.addEventListener('mouseleave', function () {
                    if (element === activeElement) {
                        activeElement = null;
                    }
                    if (globalShowTimer) {
                        clearTimeout(globalShowTimer);
                        globalShowTimer = null;
                    }
                    if (globalPopupElement) {
                        globalRemoveTimer = setTimeout(() => {
                            if (globalPopupElement && globalPopupElement.parentNode) {
                                globalPopupElement.parentNode.removeChild(globalPopupElement);
                                globalPopupElement = null;
                            }
                            globalRemoveTimer = null;
                        }, 100);
                    }
                });
            }
        });
    }

    function updatePopupPosition(event, popupElement) {
        if (!popupElement) return;
        const x = event.clientX;
        const y = event.clientY;
        const offsetX = 0;
        const offsetY = 22;
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        popupElement.style.left = (x + offsetX) + 'px';
        popupElement.style.top = (y + offsetY) + 'px';
        const rect = popupElement.getBoundingClientRect();
        const popupWidth = rect.width;
        const popupHeight = rect.height;
        let adjustedX = x + offsetX;
        let adjustedY = y + offsetY;
        if (adjustedX + popupWidth > viewportWidth) {
            adjustedX = viewportWidth - popupWidth - 5;
        }
        if (adjustedY + popupHeight > viewportHeight) {
            adjustedY = y - popupHeight - 5;
        }
        popupElement.style.left = adjustedX + 'px';
        popupElement.style.top = adjustedY + 'px';
    }

    function removeAllFileNamePopups() {
        const popups = document.querySelectorAll('.file-name.full-name-popup');
        popups.forEach(popup => {
            if (popup.parentNode) {
                popup.parentNode.removeChild(popup);
            }
        });
    }

    document.body.addEventListener('click', removeAllFileNamePopups);
    addFileNameHoverEffect();

    // 删除文件的功能
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.stopPropagation();
            const fileHash = this.getAttribute('data-hash');
            const row = this.closest('tr');
            const card = this.closest('.file-card');

            // 小屏幕卡片模式下直接删除，不显示确认框
            if (card && window.innerWidth <= 768) {
                // 添加加载状态
                const originalIcon = this.querySelector('.matsym').textContent;
                this.querySelector('.matsym').textContent = 'hourglass_empty';
                this.disabled = true;

                // 直接执行删除操作
                fetch(`/delete/${fileHash}`, {
                    method: 'POST'
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            card.remove();
                        } else {
                            alert('删除失败: ' + data.message);
                        }
                    })
                    .catch((error) => {
                        console.error('Error:', error);
                        alert('删除请求失败');
                        // 恢复按钮状态
                        this.querySelector('.matsym').textContent = originalIcon;
                        this.disabled = false;
                    });
                return;
            }

            // 桌面端表格模式显示确认框
            const container = row ? row.querySelector('td:last-child') : card.querySelector('.file-card-actions');
            if (container.querySelector('.inline-confirm')) {
                return;
            }
            const confirmDiv = document.createElement('div');
            confirmDiv.className = 'inline-confirm';
            confirmDiv.innerHTML = `
                <span>sure ?</span>
                <button class="btn btn-small btn-confirm">Yes</button>
                <button class="btn btn-small btn-cancel">No</button>
            `;
            container.appendChild(confirmDiv);
            confirmDiv.querySelector('.btn-confirm').addEventListener('click', function (e) {
                e.stopPropagation();
                fetch(`/delete/${fileHash}`, {
                    method: 'POST'
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            // 找到并移除对应的表格行或卡片
                            if (row) {
                                row.remove();
                            } else if (card) {
                                card.remove();
                            }
                        } else {
                            confirmDiv.remove();
                            alert('删除失败: ' + data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        confirmDiv.remove();
                        alert('删除请求失败');
                    });
            });
            confirmDiv.querySelector('.btn-cancel').addEventListener('click', function (e) {
                e.stopPropagation();
                confirmDiv.remove();
            });
            document.addEventListener('click', function closeConfirm(e) {
                if (!confirmDiv.contains(e.target) && document.body.contains(confirmDiv)) {
                    confirmDiv.remove();
                    document.removeEventListener('click', closeConfirm);
                }
            });
        });
    });

    // 复制分享链接的功能
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.stopPropagation(); // 阻止事件冒泡

            const fileHash = this.getAttribute('data-hash');
            const password = this.getAttribute('data-pwd');
            
            // 构造分享链接
            const shareLink = `${window.location.origin}/share?hash=${fileHash}&pwd=${password}`;
            
            // 复制到剪贴板
            navigator.clipboard.writeText(shareLink).then(() => {
                showMessage('Share link copied to clipboard', 'success');
            }).catch(err => {
                console.error('复制失败:', err);
                showMessage('复制失败，请手动复制链接', 'error');
                
                // 如果复制失败，显示链接供手动复制
                const textArea = document.createElement('textarea');
                textArea.value = shareLink;
                document.body.appendChild(textArea);
                textArea.select();
                try {
                    document.execCommand('copy');
                    showMessage('Share link copied to clipboard', 'success');
                } catch (err) {
                    console.error('手动复制也失败了:', err);
                }
                document.body.removeChild(textArea);
            });
        });
    });

    // 为下载链接添加异步下载功能，更新下载次数
    const downloadLinks = document.querySelectorAll('a[href*="/file?hash="]');
    downloadLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            
            const url = this.href;
            const fileHash = new URL(url).searchParams.get('hash');
            
            if (!fileHash) return;
            
            // 先获取文件信息
            fetch(`/api/file/${fileHash}`)
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // 保存原始按钮HTML
                        const originalHtml = link.closest('td, .file-card-actions').innerHTML;
                        
                        // 创建进度条元素
                        const progressBar = createProgressBar();
                        
                        // 替换按钮为进度条
                        const actionCell = link.closest('td, .file-card-actions');
                        actionCell.innerHTML = '';
                        actionCell.appendChild(progressBar);
                        
                        // 使用分片下载器下载文件
                        const chunkDownloader = new ChunkDownloader({
                            chunkSize: 2 * 1024 * 1024, // 2MB chunks
                            maxConcurrent: 3,
                            maxRetries: 3,
                            retryDelay: 1000,
                            onProgress: function(progress) {
                                // 更新下载进度
                                console.log(`Download progress: ${Math.round(progress.progress)}%`);
                                updateProgressBar(progressBar, Math.round(progress.progress));
                            },
                            onSuccess: function(result) {
                                // 下载成功
                                console.log('Download completed:', result);
                                showMessage('Download completed successfully!', 'success');
                                
                                // 更新下载次数显示
                                updateDownloadCount(fileHash);
                                
                                // 恢复原始按钮
                                setTimeout(() => {
                                    actionCell.innerHTML = originalHtml;
                                    // 重新绑定事件
                                    bindActionEvents();
                                }, 1000);
                            },
                            onError: function(error) {
                                // 下载失败
                                console.error('Download failed:', error);
                                showMessage('Download failed: ' + error.message, 'error');
                                
                                // 恢复原始按钮
                                actionCell.innerHTML = originalHtml;
                                // 重新绑定事件
                                bindActionEvents();
                            }
                        });

                        // 使用原始文件名
                        const filename = data.file_name || fileHash || 'download';

                        // 开始分片下载
                        chunkDownloader.downloadFile(url, filename);
                    } else {
                        console.error('Failed to get file info:', data.message);
                        showMessage('Failed to get file info: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Failed to get file info:', error);
                    showMessage('Failed to get file info', 'error');
                });
        });
    });
});

// 更新文件下载次数的函数
function updateDownloadCount(fileHash) {
    // 查找并更新对应行的下载次数
    const rows = document.querySelectorAll('.files-table tbody tr');
    for (let i = 0; i < rows.length; i++) {
        const row = rows[i];
        const hashElement = row.querySelector('.file-hash-value');
        // 检查hashElement的文本内容是否包含fileHash的前缀
        if (hashElement && hashElement.textContent.includes(fileHash.substring(0, 8))) {
            const downloadElement = row.querySelector('.file-downloads');
            if (downloadElement) {
                const currentCount = parseInt(downloadElement.textContent) || 0;
                downloadElement.textContent = currentCount + 1;
            }
            break;
        }
    }
    
    // 同样更新卡片视图中的下载次数（如果存在）
    const cards = document.querySelectorAll('.file-card');
    cards.forEach(card => {
        const hashElement = card.querySelector('.file-hash-value');
        if (hashElement && hashElement.textContent.includes(fileHash.substring(0, 8))) {
            const downloadElement = card.querySelector('.file-downloads');
            if (downloadElement) {
                const currentCount = parseInt(downloadElement.textContent) || 0;
                downloadElement.textContent = currentCount + 1;
            }
        }
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

// 创建进度条元素
function createProgressBar() {
    const progressBarContainer = document.createElement('div');
    progressBarContainer.className = 'download-progress-container';
    progressBarContainer.innerHTML = `
        <div class="download-progress-bar">
            <div class="download-progress-fill" style="width: 0%"></div>
        </div>
        <div class="download-progress-text">0%</div>
    `;
    
    // 添加样式
    progressBarContainer.style.cssText = `
        display: flex;
        align-items: center;
        gap: 10px;
        width: 100%;
    `;
    
    const progressBar = progressBarContainer.querySelector('.download-progress-bar');
    progressBar.style.cssText = `
        flex: 1;
        height: 8px;
        background-color: #e0e0e0;
        border-radius: 4px;
        overflow: hidden;
    `;
    
    const progressFill = progressBarContainer.querySelector('.download-progress-fill');
    progressFill.style.cssText = `
        height: 100%;
        background-color: #007bff;
        width: 0%;
        transition: width 0.3s ease;
    `;
    
    const progressText = progressBarContainer.querySelector('.download-progress-text');
    progressText.style.cssText = `
        font-size: 12px;
        font-weight: bold;
        min-width: 30px;
        text-align: center;
    `;
    
    return progressBarContainer;
}

// 更新进度条
function updateProgressBar(progressBarContainer, percentage) {
    const progressFill = progressBarContainer.querySelector('.download-progress-fill');
    const progressText = progressBarContainer.querySelector('.download-progress-text');
    
    if (progressFill && progressText) {
        progressFill.style.width = `${percentage}%`;
        progressText.textContent = `${percentage}%`;
    }
}

// 重新绑定事件函数
function bindActionEvents() {
    // 为下载链接添加异步下载功能，更新下载次数
    const downloadLinks = document.querySelectorAll('a[href*="/file?hash="]');
    downloadLinks.forEach(link => {
        // 检查是否已经绑定了事件
        if (!link.hasAttribute('data-download-bound')) {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                
                const url = this.href;
                const fileHash = new URL(url).searchParams.get('hash');
                
                if (!fileHash) return;
                
                // 先获取文件信息
                fetch(`/api/file/${fileHash}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            // 保存原始按钮HTML
                            const originalHtml = link.closest('td, .file-card-actions').innerHTML;
                            
                            // 创建进度条元素
                            const progressBar = createProgressBar();
                            
                            // 替换按钮为进度条
                            const actionCell = link.closest('td, .file-card-actions');
                            actionCell.innerHTML = '';
                            actionCell.appendChild(progressBar);
                            
                            // 使用分片下载器下载文件
                            const chunkDownloader = new ChunkDownloader({
                                chunkSize: 2 * 1024 * 1024, // 2MB chunks
                                maxConcurrent: 3,
                                maxRetries: 3,
                                retryDelay: 1000,
                                onProgress: function(progress) {
                                    // 更新下载进度
                                    console.log(`Download progress: ${Math.round(progress.progress)}%`);
                                    updateProgressBar(progressBar, Math.round(progress.progress));
                                },
                                onSuccess: function(result) {
                                    // 下载成功
                                    console.log('Download completed:', result);
                                    showMessage('Download completed successfully!', 'success');
                                    
                                    // 更新下载次数显示
                                    updateDownloadCount(fileHash);
                                    
                                    // 恢复原始按钮
                                    setTimeout(() => {
                                        actionCell.innerHTML = originalHtml;
                                        // 重新绑定事件
                                        bindActionEvents();
                                    }, 1000);
                                },
                                onError: function(error) {
                                    // 下载失败
                                    console.error('Download failed:', error);
                                    showMessage('Download failed: ' + error.message, 'error');
                                    
                                    // 恢复原始按钮
                                    actionCell.innerHTML = originalHtml;
                                    // 重新绑定事件
                                    bindActionEvents();
                                }
                            });

                            // 使用原始文件名
                            const filename = data.file_name || fileHash || 'download';

                            // 开始分片下载
                            chunkDownloader.downloadFile(url, filename);
                        } else {
                            console.error('Failed to get file info:', data.message);
                            showMessage('Failed to get file info: ' + data.message, 'error');
                        }
                    })
                    .catch(error => {
                        console.error('Failed to get file info:', error);
                        showMessage('Failed to get file info', 'error');
                    });
            });
            
            // 标记已绑定事件
            link.setAttribute('data-download-bound', 'true');
        }
    });

    // 复制分享链接的功能
    const copyButtons = document.querySelectorAll('.copy-btn');
    copyButtons.forEach(button => {
        if (!button.hasAttribute('data-copy-bound')) {
            button.addEventListener('click', function (e) {
                e.stopPropagation(); // 阻止事件冒泡

                const fileHash = this.getAttribute('data-hash');
                const password = this.getAttribute('data-pwd');
                
                // 构造分享链接
                const shareLink = `${window.location.origin}/share?hash=${fileHash}&pwd=${password}`;
                
                // 复制到剪贴板
                navigator.clipboard.writeText(shareLink).then(() => {
                    showMessage('Share link copied to clipboard', 'success');
                }).catch(err => {
                    console.error('复制失败:', err);
                    showMessage('复制失败，请手动复制链接', 'error');
                    
                    // 如果复制失败，显示链接供手动复制
                    const textArea = document.createElement('textarea');
                    textArea.value = shareLink;
                    document.body.appendChild(textArea);
                    textArea.select();
                    try {
                        document.execCommand('copy');
                        showMessage('Share link copied to clipboard', 'success');
                    } catch (err) {
                        console.error('手动复制也失败了:', err);
                    }
                    document.body.removeChild(textArea);
                });
            });
            
            // 标记已绑定事件
            button.setAttribute('data-copy-bound', 'true');
        }
    });

    // 删除按钮的功能
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        if (!button.hasAttribute('data-delete-bound')) {
            button.addEventListener('click', function (e) {
                e.stopPropagation(); // 阻止事件冒泡

                const fileHash = this.getAttribute('data-hash');
                const row = this.closest('tr');
                const card = this.closest('.file-card');
                const actionCell = row ? row.querySelector('td:last-child') : card.querySelector('.file-card-actions');

                // 检查是否已经有确认框
                if (actionCell && actionCell.querySelector('.inline-confirm')) {
                    return; // 如果已经有确认框，则不做任何操作
                }

                // 创建确认元素
                const confirmDiv = document.createElement('div');
                confirmDiv.className = 'inline-confirm';
                confirmDiv.innerHTML = `
                    <span>确定要删除文件吗?</span>
                    <button class="btn btn-small btn-confirm">Confirm</button>
                    <button class="btn btn-small btn-cancel">Cancel</button>
                `;

                // 添加确认元素到单元格，不替换原内容
                if (row) {
                    actionCell.appendChild(confirmDiv);
                } else {
                    card.querySelector('.file-card-actions').appendChild(confirmDiv);
                }

                // 绑定确认和取消事件
                confirmDiv.querySelector('.btn-confirm').addEventListener('click', function (e) {
                    e.stopPropagation(); // 阻止事件冒泡

                    // 执行删除操作
                    const formData = new FormData();
                    formData.append('file_hash', fileHash);

                    fetch('/files/delete', {
                        method: 'POST',
                        body: formData
                    })
                        .then(response => response.json())
                        .then(data => {
                            if (data.status === 'success') {
                                // 找到并移除对应的表格行或卡片
                                if (row) {
                                    row.remove();
                                } else {
                                    card.remove();
                                }
                                showMessage('文件删除成功', 'success');
                            } else {
                                // 移除确认元素
                                confirmDiv.remove();
                                showMessage('删除失败: ' + data.message, 'error');
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            // 移除确认元素
                            confirmDiv.remove();
                            showMessage('删除请求失败', 'error');
                        });
                });

                confirmDiv.querySelector('.btn-cancel').addEventListener('click', function (e) {
                    e.stopPropagation(); // 阻止事件冒泡
                    // 移除确认元素
                    confirmDiv.remove();
                });

                // 点击其他位置关闭确认框
                document.addEventListener('click', function closeConfirm(e) {
                    if (!confirmDiv.contains(e.target) && document.body.contains(confirmDiv)) {
                        confirmDiv.remove();
                        document.removeEventListener('click', closeConfirm);
                    }
                });
            });
            
            // 标记已绑定事件
            button.setAttribute('data-delete-bound', 'true');
        }
    });
}
