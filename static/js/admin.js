// 时区转换功能
document.addEventListener('DOMContentLoaded', function () {
    // 转换所有带有 data-utc-time 属性的元素
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
        button.addEventListener('click', function () {
            const fileHash = this.getAttribute('data-hash');
            if (confirm('Are you sure you want to delete this file?')) {
                fetch(`/delete/${fileHash}`, {
                    method: 'POST'
                })
                    .then(response => response.json())
                    .then(data => {
                        if (data.status === 'success') {
                            // 找到并移除对应的表格行，而不是刷新整个页面
                            const row = this.closest('tr');
                            row.remove();

                            // 可选：更新统计数据
                            updateStats();
                        } else {
                            alert('delete failed: ' + data.message);
                        }
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        alert('Delete request failed');
                    });
            }
        });
    });

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
});