import unittest
import os
import sys
import tempfile
import shutil
from datetime import datetime, timezone

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 设置测试环境变量
os.environ['ADMIN_USERNAME'] = 'testadmin'
os.environ['ADMIN_PASSWORD'] = 'testpass'

from services.database_service import init_db, add_user, get_user, add_file, get_file, delete_file_from_db, get_user_files, delete_user

class TestDatabase(unittest.TestCase):
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
            
    def test_add_user(self):
        """测试添加用户"""
        # 先确保用户不存在
        user = get_user('newuser')
        if user:
            delete_user('newuser')
        
        # 添加测试用户
        result = add_user('newuser', 'newpass', 0)
        self.assertTrue(result)
        
        # 验证用户已添加
        user = get_user('newuser')
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'newuser')
        
    def test_add_duplicate_user(self):
        """测试添加重复用户"""
        # 先确保用户不存在
        user = get_user('dupuser')
        if user:
            delete_user('dupuser')
        
        # 添加第一个用户
        result1 = add_user('dupuser', 'pass1', 0)
        self.assertTrue(result1)
        
        # 尝试添加同名用户
        result2 = add_user('dupuser', 'pass2', 0)
        self.assertFalse(result2)
        
    def test_get_user_with_password(self):
        """测试使用密码获取用户"""
        # 添加测试用户
        add_user('testuser', 'testpass', 0)
        
        # 使用正确密码获取用户
        user = get_user('testuser', 'testpass')
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'testuser')
        
        # 使用错误密码获取用户
        user = get_user('testuser', 'wrongpass')
        self.assertIsNone(user)
        
    def test_add_file(self):
        """测试添加文件"""
        # 添加测试用户
        add_user('testuser', 'testpass', 0)
        
        # 添加文件
        file_name = 'test.txt'
        file_hash = 'testhash123'
        file_size = 1024
        expiry_date = datetime.now(timezone.utc)
        upload_ip = '127.0.0.1'
        username = 'testuser'
        
        password = add_file(file_name, file_hash, file_size, expiry_date, upload_ip, username)
        
        # 验证密码已生成
        self.assertIsNotNone(password)
        self.assertEqual(len(password), 6)
        
        # 验证文件已添加
        file_info = get_file(file_hash)
        self.assertIsNotNone(file_info)
        self.assertEqual(file_info['file_name'], file_name)
        self.assertEqual(file_info['file_hash'], file_hash)
        self.assertEqual(file_info['file_size'], file_size)
        self.assertEqual(file_info['username'], username)
        
    def test_get_user_files(self):
        """测试获取用户文件"""
        # 添加测试用户
        add_user('testuser', 'testpass', 0)
        
        # 添加文件
        file_name = 'test.txt'
        file_hash = 'testhash123'
        file_size = 1024
        expiry_date = datetime.now(timezone.utc)
        upload_ip = '127.0.0.1'
        username = 'testuser'
        
        add_file(file_name, file_hash, file_size, expiry_date, upload_ip, username)
        
        # 获取用户文件
        files = get_user_files(username)
        # 过滤掉可能的管理员文件，只检查我们添加的文件
        user_files = [f for f in files if f['username'] == username]
        self.assertGreaterEqual(len(user_files), 1)
        # 找到我们添加的特定文件
        added_file = None
        for f in user_files:
            if f['file_hash'] == file_hash:
                added_file = f
                break
        self.assertIsNotNone(added_file)
        self.assertEqual(added_file['file_name'], file_name)
        
    def test_delete_user(self):
        """测试删除用户"""
        # 添加测试用户
        add_user('testuser', 'testpass', 0)
        
        # 验证用户存在
        user = get_user('testuser')
        self.assertIsNotNone(user)
        
        # 删除用户
        result = delete_user('testuser')
        self.assertTrue(result)
        
        # 验证用户已删除
        user = get_user('testuser')
        self.assertIsNone(user)

if __name__ == '__main__':
    unittest.main()