import unittest
import os
import sys
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.routes import app
from services.database_service import init_db, add_user, get_user, add_file, get_file, delete_file_from_db

class TestBasicFunctionality(unittest.TestCase):
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
            
    def test_index_page_anonymous(self):
        """测试匿名用户访问首页"""
        # 直接调用应用函数进行测试
        from web.routes import index
        with patch('web.routes.request') as mock_request:
            with patch('web.routes.response') as mock_response:
                with patch('web.routes.template') as mock_template:
                    mock_request.get_cookie.return_value = "anonymous"
                    mock_request.headers.get.return_value = "127.0.0.1"
                    mock_request.remote_addr = "127.0.0.1"
                    result = index()
                    # 验证模板被调用
                    mock_template.assert_called_once()
        
    def test_login_page(self):
        """测试登录页面"""
        from web.routes import login_page
        with patch('web.routes.template') as mock_template:
            result = login_page()
            mock_template.assert_called_with("views/login.html", error=None)
        
    def test_user_login_success(self):
        """测试用户登录成功"""
        from web.routes import login
        with patch('web.routes.request') as mock_request:
            with patch('web.routes.response') as mock_response:
                with patch('web.routes.authenticate_user') as mock_authenticate:
                    with patch('web.routes.redirect') as mock_redirect:
                        # 模拟表单数据
                        mock_request.forms.get.side_effect = lambda x: {'username': 'testuser', 'password': 'testpass'}.get(x)
                        mock_request.headers.get.return_value = "127.0.0.1"
                        mock_request.remote_addr = "127.0.0.1"
                        # 模拟认证成功
                        mock_authenticate.return_value = {"status": "success", "user": {"username": "testuser", "is_admin": 1}}
                        # 模拟重定向
                        mock_redirect.return_value = "redirected"
                        
                        result = login()
                        # 验证重定向被调用
                        mock_redirect.assert_called_once()
        
    def test_user_login_failure(self):
        """测试用户登录失败"""
        from web.routes import login
        with patch('web.routes.request') as mock_request:
            with patch('web.routes.response') as mock_response:
                with patch('web.routes.authenticate_user') as mock_authenticate:
                    with patch('web.routes.template') as mock_template:
                        # 模拟表单数据
                        mock_request.forms.get.side_effect = lambda x: {'username': 'wronguser', 'password': 'wrongpass'}.get(x)
                        mock_request.headers.get.return_value = "127.0.0.1"
                        mock_request.remote_addr = "127.0.0.1"
                        # 模拟认证失败
                        mock_authenticate.return_value = {"status": "error", "message": "用户名或密码错误"}
                        
                        result = login()
                        # 验证模板被调用（显示错误信息）
                        mock_template.assert_called_once()

if __name__ == '__main__':
    unittest.main()