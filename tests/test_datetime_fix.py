import unittest
import os
import sys
import tempfile
import shutil
from datetime import datetime, timezone

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.database_service import init_db, add_file, get_file, get_user_files

class TestDatetimeFix(unittest.TestCase):
    def setUp(self):
        """在每个测试之前运行"""
        # 创建临时目录用于测试
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, 'test.db')
        
        # 设置环境变量
        os.environ['DB_NAME'] = self.db_path
        
        # 初始化测试数据库
        init_db()
        
    def tearDown(self):
        """在每个测试之后运行"""
        # 清理临时目录
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
        # 清理环境变量
        if 'DB_NAME' in os.environ:
            del os.environ['DB_NAME']
            
    def test_datetime_parsing_with_z_suffix(self):
        """测试处理以'Z'结尾的ISO格式时间"""
        # 添加测试文件
        file_name = 'test.txt'
        file_hash = 'testhash123'
        file_size = 1024
        expiry_date = datetime.now(timezone.utc)
        upload_ip = '127.0.0.1'
        username = 'testuser'
        
        # 添加文件
        add_file(file_name, file_hash, file_size, expiry_date, upload_ip, username)
        
        # 获取文件信息
        file_info = get_file(file_hash)
        self.assertIsNotNone(file_info)
        
        # 验证时间格式正确解析
        self.assertIn('upload_date', file_info)
        self.assertIn('expiry_date', file_info)
        
        # 验证时间是字符串格式
        self.assertIsInstance(file_info['upload_date'], str)
        self.assertIsInstance(file_info['expiry_date'], str)
        
    def test_get_user_files_datetime_handling(self):
        """测试get_user_files函数中的时间处理"""
        # 添加测试文件
        file_name = 'test.txt'
        file_hash = 'testhash123'
        file_size = 1024
        expiry_date = datetime.now(timezone.utc)
        upload_ip = '127.0.0.1'
        username = 'testuser'
        
        # 添加文件
        add_file(file_name, file_hash, file_size, expiry_date, upload_ip, username)
        
        # 获取用户文件
        files = get_user_files(username)
        
        # 验证至少有一个文件
        self.assertGreaterEqual(len(files), 1)
        
        # 验证时间字段存在且为字符串格式
        file_found = False
        for file in files:
            if file['file_hash'] == file_hash:
                file_found = True
                self.assertIn('upload_date', file)
                self.assertIn('expiry_date', file)
                self.assertIsInstance(file['upload_date'], str)
                self.assertIsInstance(file['expiry_date'], str)
                break
        
        self.assertTrue(file_found, "添加的文件未在用户文件列表中找到")

if __name__ == '__main__':
    unittest.main()