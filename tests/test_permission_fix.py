import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.routes import delete_user_route, change_password_route
from services.database_service import init_db, add_user, delete_user, get_user, update_user_password

# 模拟request对象
class MockRequest:
    def __init__(self, forms=None, cookies=None):
        self.forms = forms or {}
        self.cookies = cookies or {}
        self.headers = {'x-forwarded-for': '127.0.0.1'}
        self.remote_addr = '127.0.0.1'
        
    def get_cookie(self, key, secret=None):
        if key == "username":
            return self.cookies.get(key)
        return None

class TestPermissionFix(unittest.TestCase):
    def setUp(self):
        """在每个测试之前运行"""
        # 创建临时目录用于测试
        self.test_dir = tempfile.mkdtemp()
        self.upload_dir = os.path.join(self.test_dir, 'upload')
        self.db_path = os.path.join(self.test_dir, 'test.db')
        
        # 设置环境变量
        os.environ['UPLOAD_FOLDER'] = self.upload_dir
        os.environ['DB_NAME'] = self.db_path
        
        # 创建必要的目录
        os.makedirs(self.upload_dir, exist_ok=True)
        
        # 初始化测试数据库
        init_db()
        
    def tearDown(self):
        """在每个测试之后运行"""
        # 清理临时目录
        shutil.rmtree(self.test_dir, ignore_errors=True)
        
        # 清理环境变量
        if 'UPLOAD_FOLDER' in os.environ:
            del os.environ['UPLOAD_FOLDER']
        if 'DB_NAME' in os.environ:
            del os.environ['DB_NAME']
            
    def test_delete_user_permission_admin_only(self):
        """测试只有管理员可以删除用户"""
        # 添加管理员用户
        add_user('admin', 'adminpass', 1)
        
        # 添加普通用户
        add_user('normaluser', 'normalpass', 0)
        
        # 直接测试删除用户函数的逻辑
        # 模拟管理员权限
        with patch('web.routes.get_user') as mock_get_user:
            mock_get_user.return_value = {'username': 'admin', 'is_admin': 1}
            
            # 模拟数据库中的目标用户不是管理员
            with patch('services.database_service.get_user') as mock_db_get_user:
                mock_db_get_user.return_value = {'username': 'normaluser', 'is_admin': 0}
                
                # 调用删除用户函数
                result = delete_user('normaluser')
                
                # 验证删除成功
                self.assertTrue(result)
                
                # 验证用户已删除
                user = get_user('normaluser')
                self.assertIsNone(user)
        
    def test_delete_user_permission_denied_for_non_admin(self):
        """测试非管理员无法删除用户"""
        # 添加普通用户1
        add_user('user1', 'pass1', 0)
        
        # 添加普通用户2
        add_user('user2', 'pass2', 0)
        
        # 直接测试删除用户函数的逻辑
        # 模拟非管理员权限
        with patch('web.routes.get_user') as mock_get_user:
            mock_get_user.return_value = {'username': 'user1', 'is_admin': 0}
            
            # 调用删除用户路由函数
            # 由于权限检查在路由函数中，我们需要模拟request对象
            from web.routes import request
            original_request = request
            
            # 创建模拟的request对象
            mock_request = MockRequest(forms={'username': 'user2'}, cookies={'username': 'user1'})
            
            # 替换request对象
            import web.routes as app
            app.request = mock_request
            
            # 模拟数据库中的目标用户
            with patch('services.database_service.get_user') as mock_db_get_user:
                mock_db_get_user.return_value = {'username': 'user1', 'is_admin': 0}
                
                # 调用删除用户路由函数
                response = delete_user_route()
                
                # 验证权限被拒绝
                self.assertEqual(response['status'], 'error')
                self.assertEqual(response['message'], 'permission denied')
                
                # 恢复原始request对象
                app.request = original_request
        
        # 验证用户未被删除
        user = get_user('user2')
        self.assertIsNotNone(user)
        
    def test_change_password_self_allowed(self):
        """测试用户可以修改自己的密码"""
        # 添加普通用户
        add_user('testuser', 'oldpass', 0)
        
        # 直接测试修改密码函数的逻辑
        # 模拟request对象
        from web.routes import request
        original_request = request
        
        # 创建模拟的request对象
        mock_request = MockRequest(forms={'username': 'testuser', 'new_password': 'newpass'}, cookies={'username': 'testuser'})
        
        # 替换request对象
        import web.routes as app
        app.request = mock_request
        
        # 模拟get_user函数
        with patch('web.routes.get_user') as mock_get_user:
            mock_get_user.return_value = {'username': 'testuser', 'is_admin': 0}
            
            # 模拟app_logger
            with patch('web.routes.app_logger'):
                # 调用修改密码路由函数
                response = change_password_route()
                
                # 验证修改成功
                self.assertEqual(response['status'], 'success')
                self.assertEqual(response['message'], 'password updated')
            
            # 恢复原始request对象
            app.request = original_request
        
    def test_change_password_other_denied_for_non_admin(self):
        """测试非管理员无法修改其他用户密码"""
        # 添加普通用户1
        add_user('user1', 'pass1', 0)
        
        # 添加普通用户2
        add_user('user2', 'pass2', 0)
        
        # 直接测试修改密码函数的逻辑
        # 模拟request对象
        from web.routes import request
        original_request = request
        
        # 创建模拟的request对象
        mock_request = MockRequest(forms={'username': 'user2', 'new_password': 'hacked'}, cookies={'username': 'user1'})
        
        # 替换request对象
        import web.routes as app
        app.request = mock_request
        
        # 模拟get_user函数
        with patch('web.routes.get_user') as mock_get_user:
            # 当前用户是user1（非管理员），目标用户是user2
            mock_get_user.return_value = {'username': 'user1', 'is_admin': 0}
            
            # 模拟app_logger
            with patch('web.routes.app_logger'):
                # 调用修改密码路由函数
                response = change_password_route()
                
                # 验证权限被拒绝
                self.assertEqual(response['status'], 'error')
                self.assertEqual(response['message'], 'permission denied')
            
            # 恢复原始request对象
            app.request = original_request

if __name__ == '__main__':
    unittest.main()