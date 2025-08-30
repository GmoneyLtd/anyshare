// 时区转换功能
document.addEventListener('DOMContentLoaded', function () {
    // 定义一个移除所有文件名提示框的函数
    function removeAllFileNamePopups() {
        const popups = document.querySelectorAll('.file-name.full-name-popup');
        popups.forEach(popup => {
            if (popup.parentNode) {
                popup.parentNode.removeChild(popup);
            }
        });
    }

    // 页面加载时立即移除所有可能残留的提示框
    removeAllFileNamePopups();

    // 为页面添加全局点击事件，确保点击任何地方时移除所有提示框
    document.body.addEventListener('click', function () {
        removeAllFileNamePopups();
    });

    // 为文件名添加悬停显示完整内容的功能
    function addFileNameHoverEffect() {
        // 查找所有文件名容器（包括表格和卡片中的）
        const fileNameContainers = document.querySelectorAll('.file-name-container');
        // 创建一个全局的提示框元素，避免创建多个
        let globalPopupElement = null;
        let globalRemoveTimer = null;
        let globalShowTimer = null;
        let activeElement = null;

        fileNameContainers.forEach(container => {
            // 获取文件名元素
            const element = container.querySelector('.file-name');

            // 检查元素是否存在以及是否可能被截断
            if (element && element.scrollWidth > element.offsetWidth) {
                element.addEventListener('mouseenter', function (e) {
                    // 设置当前活动元素
                    activeElement = element;

                    // 清除之前的定时器
                    if (globalRemoveTimer) {
                        clearTimeout(globalRemoveTimer);
                        globalRemoveTimer = null;
                    }

                    // 延迟显示，避免鼠标快速移动时频繁触发
                    // 浏览器默认提示框通常有300-500ms延迟
                    globalShowTimer = setTimeout(() => {
                        // 先移除可能存在的其他提示框
                        removeAllFileNamePopups();

                        // 创建悬浮显示的完整文件名
                        globalPopupElement = document.createElement('div');
                        globalPopupElement.className = 'file-name full-name-popup';
                        globalPopupElement.textContent = element.textContent;
                        globalPopupElement.setAttribute('role', 'tooltip');
                        globalPopupElement.setAttribute('aria-label', element.textContent);
                        globalPopupElement.id = 'filename-popup'; // 使用固定ID

                        // 设置初始位置
                        updatePopupPosition(e, globalPopupElement);

                        // 添加到文档中
                        document.body.appendChild(globalPopupElement);
                    }, 500); // 使用500ms延迟，更接近浏览器默认行为
                });

                // 鼠标移动时不需要立即更新位置，可以添加节流来优化性能
                let lastMoveTime = 0;
                element.addEventListener('mousemove', function (e) {
                    // 只有当前元素是活动元素时才更新位置
                    if (globalPopupElement && element === activeElement) {
                        // 简单的节流，每50ms更新一次位置
                        const now = Date.now();
                        if (now - lastMoveTime > 50) {
                            lastMoveTime = now;
                            // 更新位置
                            updatePopupPosition(e, globalPopupElement);
                        }
                    }
                });

                element.addEventListener('mouseleave', function () {
                    // 清除当前活动元素
                    if (element === activeElement) {
                        activeElement = null;
                    }

                    // 清除显示定时器
                    if (globalShowTimer) {
                        clearTimeout(globalShowTimer);
                        globalShowTimer = null;
                    }

                    // 延迟移除提示框，避免快速移动鼠标时闪烁
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

    // 更新弹出框位置的函数
    function updatePopupPosition(event, popupElement) {
        if (!popupElement) return;

        // 获取鼠标位置
        const x = event.clientX;
        const y = event.clientY;

        // 提示框位置计算 - 默认在鼠标正下方，与浏览器默认提示框类似
        const offsetX = 0; // 水平偏移为0，正好在鼠标下方
        const offsetY = 22; // 垂直偏移，在鼠标下方约22像素

        // 获取视窗尺寸
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        // 先设置位置，这样才能获取准确的尺寸
        popupElement.style.left = (x + offsetX) + 'px';
        popupElement.style.top = (y + offsetY) + 'px';

        // 获取弹出框尺寸
        const rect = popupElement.getBoundingClientRect();
        const popupWidth = rect.width;
        const popupHeight = rect.height;

        // 调整位置以确保弹出框不会超出视窗
        let adjustedX = x + offsetX;
        let adjustedY = y + offsetY;

        // 确保提示框不会超出右侧边界
        if (adjustedX + popupWidth > viewportWidth) {
            adjustedX = viewportWidth - popupWidth - 5;
        }

        // 确保提示框不会超出底部边界
        if (adjustedY + popupHeight > viewportHeight) {
            // 如果下方空间不足，则显示在鼠标上方
            adjustedY = y - popupHeight - 5;
        }

        // 应用最终位置
        popupElement.style.left = adjustedX + 'px';
        popupElement.style.top = adjustedY + 'px';
    }

    // 页面加载完成后添加文件名悬停效果
    addFileNameHoverEffect();

    // 检查模态框元素是否存在
    const expiryModal = document.getElementById('expiry-modal');
    if (!expiryModal) {
        console.error('找不到过期时间模态框元素，请检查HTML代码');
    }

    // 检查表单元素是否存在
    const modalExpiryForm = document.getElementById('modal-expiry-form');
    if (!modalExpiryForm) {
        console.error('找不到过期时间调整表单元素，请检查HTML代码');
    } else {
        // 过期时间调整表单提交事件
        modalExpiryForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const fileHashElement = document.getElementById('modal-file-hash');
            const expirySelectElement = document.getElementById('modal-expiry-select');

            if (!fileHashElement || !expirySelectElement) {
                showMessage('表单元素不存在', 'error');
                return;
            }

            const fileHash = fileHashElement.value;
            const newExpiry = expirySelectElement.value;

            // 发送请求更新过期时间
            fetch('/update_expiry', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `file_hash=${fileHash}&expiry=${newExpiry}`
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // 关闭模态框
                        closeExpiryModal();

                        // 查找并更新对应行的过期时间单元格
                        const rows = document.querySelectorAll('.files-table tbody tr');
                        for (let i = 0; i < rows.length; i++) {
                            const row = rows[i];
                            const hashElement = row.querySelector('.file-hash-value');
                            if (hashElement && hashElement.textContent === `(${fileHash})`) {
                                const expiryCell = row.querySelector('td:nth-child(6)');

                                // 更新页面显示
                                expiryCell.innerHTML = `
                                <div class="time-info">
                                    <div class="time-relative">${data.expiry_relative}</div>
                                    <div class="time-absolute" data-utc-time="${data.expiry_date}">
                                        (${data.expiry_formatted})
                                    </div>
                                </div>
                            `;

                                // 重新应用时区转换
                                const newTimeElement = expiryCell.querySelector('[data-utc-time]');
                                if (newTimeElement) {
                                    const utcTimeStr = newTimeElement.getAttribute('data-utc-time');
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
                                            newTimeElement.textContent = `(${localTimeStr})`;
                                        } catch (e) {
                                            console.error('时间转换错误:', e);
                                        }
                                    }
                                }
                                break;
                            }
                        }

                        showMessage('文件过期时间已更新', 'success');
                    } else {
                        showMessage('更新失败: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showMessage('更新请求失败', 'error');
                });
        });
    }

    // 加载用户列表
    loadUsersList();

    // 时区转换功能
    const timeElements = document.querySelectorAll('[data-utc-time]');

    timeElements.forEach(element => {
        const utcTimeStr = element.getAttribute('data-utc-time');
        if (utcTimeStr) {
            try {
                // 解析 UTC 时间
                const utcDate = new Date(utcTimeStr);

                // 格式化为本地时间
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

                // 更新显示
                element.textContent = `(${localTimeStr})`;
            } catch (e) {
                console.error('时间转换错误:', e);
            }
        }
    });

    // 删除文件的功能
    const deleteButtons = document.querySelectorAll('.delete-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.stopPropagation(); // 阻止事件冒泡

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
                            updateStats();
                        } else {
                            showMessage('删除失败: ' + data.message, 'error');
                        }
                    })
                    .catch((error) => {
                        console.error('Error:', error);
                        showMessage('删除请求失败', 'error');
                        // 恢复按钮状态
                        this.querySelector('.matsym').textContent = originalIcon;
                        this.disabled = false;
                    });
                return;
            }

            // 桌面端表格模式显示确认框
            const container = row ? row.querySelector('td:last-child') : card.querySelector('.file-card-actions');

            // 检查是否已经有确认框
            if (container.querySelector('.inline-confirm')) {
                return; // 如果已经有确认框，则不做任何操作
            }

            // 创建确认元素
            const confirmDiv = document.createElement('div');
            confirmDiv.className = 'inline-confirm';
            confirmDiv.innerHTML = `
                <span>sure ?</span>
                <button class="btn btn-small btn-confirm">Yes</button>
                <button class="btn btn-small btn-cancel">No</button>
            `;

            // 添加确认元素到容器，不替换原内容
            container.appendChild(confirmDiv);

            // 绑定确认和取消事件
            confirmDiv.querySelector('.btn-confirm').addEventListener('click', function (e) {
                e.stopPropagation(); // 阻止事件冒泡

                // 执行删除操作
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

                            // 可选：更新统计数据
                            updateStats();
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
    });

    // 修改文件过期时间的功能
    const extendButtons = document.querySelectorAll('.extend-btn');
    extendButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.stopPropagation(); // 阻止事件冒泡

            const fileHash = this.getAttribute('data-hash');
            const row = this.closest('tr');
            const card = this.closest('.file-card');

            // 根据是表格还是卡片来查找文件名
            const fileNameElement = row ? row.querySelector('.file-name') : card.querySelector('.file-name');
            const fileName = fileNameElement ? fileNameElement.textContent : '';

            // 打开模态框
            openExpiryModal(fileHash, fileName);
        });
    });

    // 删除用户的功能
    const deleteUserButtons = document.querySelectorAll('.delete-user-btn');
    deleteUserButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.stopPropagation(); // 阻止事件冒泡

            const username = this.getAttribute('data-username');
            const row = this.closest('tr');
            const actionCell = row.querySelector('td:last-child');

            // 检查是否已经有确认框
            if (actionCell && actionCell.querySelector('.inline-confirm')) {
                return; // 如果已经有确认框，则不做任何操作
            }

            // 创建确认元素
            const confirmDiv = document.createElement('div');
            confirmDiv.className = 'inline-confirm';
            confirmDiv.innerHTML = `
                <span>确定要删除用户 ${username} 吗?</span>
                <button class="btn btn-small btn-confirm">Confirm</button>
                <button class="btn btn-small btn-cancel">Cancel</button>
            `;

            // 添加确认元素到单元格，不替换原内容
            actionCell.appendChild(confirmDiv);

            // 绑定确认和取消事件
            confirmDiv.querySelector('.btn-confirm').addEventListener('click', function (e) {
                e.stopPropagation(); // 阻止事件冒泡

                // 执行删除操作
                const formData = new FormData();
                formData.append('username', username);

                fetch('/users/delete', {
                    method: 'POST',
                    body: formData
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            // 找到并移除对应的表格行
                            row.remove();
                            showMessage('用户删除成功', 'success');
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
    });

    // 配置表单提交处理
    const configForm = document.getElementById('config-form');
    if (configForm) {
        configForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const formData = new FormData(this);

            fetch('/admin/config', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // 配置保存成功后，从后端获取当前配置状态并更新UI
                        fetch('/admin/config', {
                            method: 'GET'
                        })
                            .then(response => response.json())
                            .then(configData => {
                                if (configData.status === 'success') {
                                    // 更新单选按钮的状态
                                    const anonymousEnabled = document.getElementById('anonymous-enabled');
                                    const anonymousDisabled = document.getElementById('anonymous-disabled');

                                    if (anonymousEnabled && anonymousDisabled) {
                                        anonymousEnabled.checked = (configData.anonymous === 'true');
                                        anonymousDisabled.checked = (configData.anonymous === 'false');
                                    }
                                }
                                showMessage('Configuration saved successfully', 'success');
                            })
                            .catch(error => {
                                console.error('Error fetching config:', error);
                                showMessage('Configuration saved but failed to update UI', 'error');
                            });
                    } else {
                        showMessage('Failed to save configuration: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showMessage('Failed to save configuration', 'error');
                });
        });
    } else {
        console.warn('Config form not found in the DOM');
    }

    // 可选：更新统计数据的函数
    function updateStats() {
        fetch('/admin/stats', {
            method: 'GET'
        })
            .then(response => response.json())
            .then(data => {
                document.querySelectorAll('.stat-value')[0].textContent = data.active_files;
                document.querySelectorAll('.stat-value')[1].textContent =
                    `${data.storage_used} / ${data.storage_limit}`;
            })
            .catch(error => {
                console.error('Error updating stats:', error);
            });
    }

    // 加载用户列表的函数
    function loadUsersList() {
        fetch('/admin/users', {
            method: 'GET'
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    const usersTableBody = document.getElementById('users-table-body');
                    const usersCardsBody = document.getElementById('users-cards-body');
                    usersTableBody.innerHTML = '';
                    usersCardsBody.innerHTML = '';

                    data.users.forEach(user => {
                        // 生成表格行
                        const row = document.createElement('tr');
                        row.innerHTML = `
                        <td>${user.username}</td>
                        <td>${user.is_admin === 1 ? 'Admin' : 'User'}</td>
                        <td>
                            <button class="nav-link btn-icon change-password-btn" data-username="${user.username}" title="Change Password">
                                <span class="matsym">key</span>
                            </button>
                            ${user.is_admin === 1 ? '' : `<button class="nav-link btn-icon delete-user-btn" data-username="${user.username}" title="Delete User">
                                <span class="matsym">delete_forever</span>
                            </button>`}
                        </td>
                    `;
                        usersTableBody.appendChild(row);

                        // 生成卡片
                        const card = document.createElement('div');
                        card.className = 'user-card';
                        card.innerHTML = `
                        <div class="user-card-info">
                            <div class="user-card-username">${user.username}</div>
                            <div class="user-card-role">
                                <span class="matsym">${user.is_admin === 1 ? 'admin_panel_settings' : 'person'}</span>
                                <span>${user.is_admin === 1 ? 'Admin' : 'User'}</span>
                            </div>
                        </div>
                        <div class="user-card-actions">
                            <button class="nav-link btn-icon change-password-btn" data-username="${user.username}" title="Change Password">
                                <span class="matsym">key</span>
                            </button>
                            ${user.is_admin === 1 ? '' : `<button class="nav-link btn-icon delete-user-btn" data-username="${user.username}" title="Delete User">
                                <span class="matsym">delete_forever</span>
                            </button>`}
                        </div>
                    `;
                        usersCardsBody.appendChild(card);
                    });

                    // 为每个更改密码按钮添加事件监听器
                    document.querySelectorAll('.change-password-btn').forEach(button => {
                        button.addEventListener('click', function () {
                            const username = this.getAttribute('data-username');
                            openPasswordModal(username);
                        });
                    });

                    // 为每个删除用户按钮添加事件监听器
                    document.querySelectorAll('.delete-user-btn').forEach(button => {
                        button.addEventListener('click', function (e) {
                            e.stopPropagation(); // 阻止事件冒泡

                            const username = this.getAttribute('data-username');
                            const row = this.closest('tr');
                            const card = this.closest('.user-card');

                            // 小屏幕卡片模式下直接删除，不显示确认框
                            if (card && window.innerWidth <= 768) {
                                // 添加加载状态
                                const originalIcon = this.querySelector('.matsym').textContent;
                                this.querySelector('.matsym').textContent = 'hourglass_empty';
                                this.disabled = true;

                                // 直接执行删除操作
                                const formData = new FormData();
                                formData.append('username', username);

                                fetch('/users/delete', {
                                    method: 'POST',
                                    body: formData
                                })
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.status === 'success') {
                                            card.remove();
                                            showMessage('User deleted successfully', 'success');
                                        } else {
                                            showMessage('Failed to delete: ' + data.message, 'error');
                                            // 恢复按钮状态
                                            this.querySelector('.matsym').textContent = originalIcon;
                                            this.disabled = false;
                                        }
                                    })
                                    .catch((error) => {
                                        console.error('Error:', error);
                                        showMessage('Delete request failed', 'error');
                                        // 恢复按钮状态
                                        this.querySelector('.matsym').textContent = originalIcon;
                                        this.disabled = false;
                                    });
                                return;
                            }

                            // 桌面端表格模式显示确认框
                            const actionCell = row.querySelector('td:last-child');

                            // 检查是否已经有确认框
                            if (actionCell && actionCell.querySelector('.inline-confirm')) {
                                return; // 如果已经有确认框，则不做任何操作
                            }

                            // 创建确认元素
                            const confirmDiv = document.createElement('div');
                            confirmDiv.className = 'inline-confirm';
                            confirmDiv.innerHTML = `
                                <span>Delete user ${username}?</span>
                                <button class="btn btn-small btn-confirm">Confirm</button>
                                <button class="btn btn-small btn-cancel">Cancel</button>
                            `;

                            // 添加确认元素到单元格，不替换原内容
                            actionCell.appendChild(confirmDiv);

                            // 绑定确认和取消事件
                            confirmDiv.querySelector('.btn-confirm').addEventListener('click', function (e) {
                                e.stopPropagation(); // 阻止事件冒泡

                                // 执行删除操作
                                const formData = new FormData();
                                formData.append('username', username);

                                fetch('/users/delete', {
                                    method: 'POST',
                                    body: formData
                                })
                                    .then(response => response.json())
                                    .then(data => {
                                        if (data.status === 'success') {
                                            // 找到并移除对应的表格行和卡片
                                            if (row) {
                                                row.remove();
                                            }
                                            // 同时移除对应的卡片
                                            const correspondingCard = document.querySelector(`.user-card .delete-user-btn[data-username="${username}"]`)?.closest('.user-card');
                                            if (correspondingCard) {
                                                correspondingCard.remove();
                                            }
                                            showMessage('User deleted successfully', 'success');
                                        } else {
                                            // 移除确认元素
                                            confirmDiv.remove();
                                            showMessage('Failed to delete: ' + data.message, 'error');
                                        }
                                    })
                                    .catch(error => {
                                        console.error('Error:', error);
                                        // 移除确认元素
                                        confirmDiv.remove();
                                        showMessage('Delete request failed', 'error');
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
                    });
                } else {
                    console.error('Failed to load users:', data.message);
                }
            })
            .catch(error => {
                console.error('Error loading users:', error);
            });
    }

    // 打开密码修改模态框
    function openPasswordModal(username) {
        document.getElementById('modal-username').textContent = username;
        document.getElementById('modal-password-form').reset();
        document.getElementById('password-modal').style.display = 'flex';
    }

    // 关闭密码修改模态框
    function closePasswordModal() {
        document.getElementById('password-modal').style.display = 'none';
    }

    // 打开过期时间调整模态框
    function openExpiryModal(fileHash, fileName) {
        const filenameElement = document.getElementById('modal-filename');
        if (filenameElement) {
            filenameElement.textContent = fileName ? `for ${fileName}` : '';
        }

        const fileHashElement = document.getElementById('modal-file-hash');
        if (fileHashElement) {
            fileHashElement.value = fileHash;
        } else {
            console.error('找不到文件哈希输入元素');
        }

        const formElement = document.getElementById('modal-expiry-form');
        if (formElement) {
            formElement.reset();
        }

        const modalElement = document.getElementById('expiry-modal');
        if (modalElement) {
            modalElement.style.display = 'flex';
        } else {
            console.error('找不到过期时间模态框元素');
        }
    }

    // 关闭过期时间调整模态框
    function closeExpiryModal() {
        const modalElement = document.getElementById('expiry-modal');
        if (modalElement) {
            modalElement.style.display = 'none';
        }
    }

    // 取消密码修改按钮事件
    const cancelPasswordBtn = document.getElementById('cancel-password-change');
    if (cancelPasswordBtn) {
        cancelPasswordBtn.addEventListener('click', closePasswordModal);
    }

    // 取消过期时间调整按钮事件
    const cancelExpiryBtn = document.getElementById('cancel-expiry-change');
    if (cancelExpiryBtn) {
        cancelExpiryBtn.addEventListener('click', closeExpiryModal);
    }

    // 密码修改表单提交事件
    const passwordForm = document.getElementById('modal-password-form');
    if (passwordForm) {
        passwordForm.addEventListener('submit', function (e) {
            e.preventDefault();

            const username = document.getElementById('modal-username').textContent;
            const newPassword = document.getElementById('modal-new-password').value;
            const confirmPassword = document.getElementById('modal-confirm-password').value;

            // 验证密码确认
            if (newPassword !== confirmPassword) {
                showMessage('密码不匹配', 'error');
                return;
            }

            // 发送密码修改请求
            const formData = new FormData();
            formData.append('username', username);
            formData.append('new_password', newPassword);

            fetch('/users/change_password', {
                method: 'POST',
                body: formData
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        showMessage('密码修改成功', 'success');
                        closePasswordModal();
                    } else {
                        showMessage('密码修改失败: ' + data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showMessage('密码修改失败', 'error');
                });
        });
    }
});

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