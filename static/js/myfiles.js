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
});
