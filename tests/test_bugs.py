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

class TestBugFixes(unittest.TestCase):
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
            
    def test_add_user_and_delete_user(self):
        """测试添加用户和删除用户功能"""
        # 先确保用户不存在
        user = get_user('testuser')
        if user:
            delete_user('testuser')
        
        # 添加测试用户
        result = add_user('testuser', 'testpass', 0)
        self.assertTrue(result)
        
        # 验证用户已添加
        user = get_user('testuser')
        self.assertIsNotNone(user)
        self.assertEqual(user['username'], 'testuser')
        
        # 删除用户
        result = delete_user('testuser')
        self.assertTrue(result)
        
        # 验证用户已删除
        user = get_user('testuser')
        self.assertIsNone(user)

if __name__ == '__main__':
    unittest.main()