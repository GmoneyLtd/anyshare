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
                    <div class="progress-fill" style="width: 0%; height: 100%; background: rgb(233, 93, 114); transition: width 0.3s;"></div>
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
                    window.open(link.href, '_blank');
                }
            });
            
            // 开始分片下载
            chunkDownloader.downloadFile(fileHash, password);
        });
    });
});
