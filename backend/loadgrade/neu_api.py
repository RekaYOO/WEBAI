import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, Union

import requests
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class NEUAPI:
    def __init__(self, config_path: str, data_dir: str):
        """
        初始化NEU API客户端
        
        Args:
            config_path: 配置文件路径
            data_dir: 数据存储目录路径
        """
        self.session = self._prepare_session()
        self.config_path = config_path
        self.config = self._load_config()
        self.is_logged_in = False
        
        # 创建输出目录
        self.output_dir = Path(data_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_config(self):
        """保存配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=4, ensure_ascii=False)
    
    def _save_file(self, content: Union[str, Dict], filename: str) -> str:
        """
        保存内容到文件
        
        Args:
            content: 要保存的内容（字符串或字典）
            filename: 文件名
            
        Returns:
            str: 保存的文件路径
        """
        output_path = self.output_dir / filename
        
        if isinstance(content, dict):
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(content, f, indent=4, ensure_ascii=False)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        return str(output_path)
    
    def _prepare_session(self) -> requests.Session:
        """准备会话对象"""
        sess = requests.Session()
        sess.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
            "Accept": "application/json",
            "Accept-Language": "zh-CN",
            "Accept-Encoding": "gzip, deflate",
            "X-Requested-With": "XMLHttpRequest",
            "Connection": "keep-alive"
        })
        return sess
    
    def _get_login_form_data(self) -> Dict[str, str]:
        """获取登录表单数据"""
        response = self.session.get("https://pass.neu.edu.cn/tpass/login")
        page_soup = BeautifulSoup(response.text, "html.parser")
        form = page_soup.find("form", {'id': 'loginForm'})
        
        return {
            "form_lt_string": form.find("input", {'id': 'lt'}).attrs["value"],
            "form_destination": form.attrs['action'],
            "form_execution": form.find("input", {'name': 'execution'}).attrs["value"]
        }
    
    def login(self) -> Tuple[bool, str]:
        """
        登录统一身份认证系统
        
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        try:
            if self.is_logged_in:
                return True, "已经处于登录状态"
                
            # 获取登录表单数据
            form_data = self._get_login_form_data()
            
            # 准备登录数据
            username = self.config['user_info']['username']
            password = self.config['user_info']['password']
            
            login_data = {
                'rsa': username + password + form_data['form_lt_string'],
                'ul': len(username),
                'pl': len(password),
                'lt': form_data['form_lt_string'],
                'execution': form_data['form_execution'],
                '_eventId': 'submit'
            }
            
            # 提交登录请求
            response = self.session.post(
                "https://pass.neu.edu.cn" + form_data['form_destination'],
                data=login_data,
                allow_redirects=True
            )
            
            # 检查登录结果
            soup = BeautifulSoup(response.text, "html.parser")
            title = soup.find("title")
            
            if not title:
                raise Exception("后端服务异常")
            
            page_title = title.text
            if page_title == "智慧东大--统一身份认证":
                raise Exception("用户名或密码错误")
            
            # 更新登录历史
            login_record = {
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            self.config['login_history'].append(login_record)
            self.config['last_login'] = login_record
            self._save_config()
            
            self.is_logged_in = True
            return True, "登录成功"
            
        except Exception as e:
            # 更新登录历史
            login_record = {
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
            self.config['login_history'].append(login_record)
            self.config['last_login'] = login_record
            self._save_config()
            
            self.is_logged_in = False
            return False, f"登录失败: {str(e)}"
    
    def get_grades(self, save_to_file: bool = True) -> Tuple[bool, Union[str, str]]:
        """
        获取历史成绩
        
        Args:
            save_to_file: 是否保存到文件，默认为True
            
        Returns:
            Tuple[bool, Union[str, str]]: (是否成功, HTML内容或错误信息)
        """
        try:
            if not self.is_logged_in:
                return False, "请先登录"
                
            # 获取历史成绩
            response = self.session.post(
                "http://219.216.96.4/eams/teach/grade/course/person!historyCourseGrade.action",
                params={"projectType": "MAJOR"},
                headers={
                    "Accept": "*/*",
                    "X-Requested-With": "XMLHttpRequest",
                    "Origin": "http://219.216.96.4",
                    "Referer": "http://219.216.96.4/eams/teach/grade/course/person!search.action?semesterId=111&projectType=",
                    "Accept-Language": "zh-CN,zh;q=0.9"
                }
            )
            
            # 检查响应状态码
            if response.status_code != 200:
                return False, f"请求失败，状态码: {response.status_code}"
            
            result = response.text
            
            if save_to_file:
                file_path = self._save_file(result, "grades.html")
                return True, {"data": result, "file_path": file_path}
            
            return True, result
            
        except Exception as e:
            return False, f"获取成绩失败: {str(e)}"
    
    def get_plan(self, save_to_file: bool = True) -> Tuple[bool, Union[str, str]]:
        """
        获取培养计划
        
        Args:
            save_to_file: 是否保存到文件，默认为True
            
        Returns:
            Tuple[bool, Union[str, str]]: (是否成功, HTML内容或错误信息)
        """
        try:
            if not self.is_logged_in:
                return False, "请先登录"
                
            # 访问培养计划页面
            response = self.session.get(
                "http://219.216.96.4/eams/myPlan.action",
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Referer": "http://219.216.96.4/eams/homeExt.action"
                }
            )
            
            result = response.text
            
            if save_to_file:
                file_path = self._save_file(result, "plan.html")
                return True, {"data": result, "file_path": file_path}
            
            return True, result
            
        except Exception as e:
            return False, f"获取培养计划失败: {str(e)}"
    
    def get_plan_completion(self, save_to_file: bool = True) -> Tuple[bool, Union[str, str]]:
        """
        获取培养计划完成情况
        
        Args:
            save_to_file: 是否保存到文件，默认为True
            
        Returns:
            Tuple[bool, Union[str, str]]: (是否成功, HTML内容或错误信息)
        """
        try:
            if not self.is_logged_in:
                return False, "请先登录"
                
            # 访问培养计划完成情况页面
            response = self.session.get(
                "http://219.216.96.4/eams/myPlanCompl.action",
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                    "Referer": "http://219.216.96.4/eams/myPlan.action"
                }
            )
            
            result = response.text
            
            if save_to_file:
                file_path = self._save_file(result, "plan_completion.html")
                return True, {"data": result, "file_path": file_path}
            
            return True, result
            
        except Exception as e:
            return False, f"获取培养计划完成情况失败: {str(e)}"

def main():
    """使用示例"""
    api = NEUAPI("backend/loadgrade/config.json", "backend/data")
    
    # 登录
    success, message = api.login()
    print(f"登录结果: {message}")
    
    if success:
        # 获取成绩
        success, result = api.get_grades()
        print(f"获取成绩结果: {'成功' if success else result}")
        
        # 获取培养计划
        success, result = api.get_plan()
        print(f"获取培养计划结果: {'成功' if success else result}")
        
        # 获取培养计划完成情况
        success, result = api.get_plan_completion()
        print(f"获取培养计划完成情况结果: {'成功' if success else result}")

if __name__ == "__main__":
    main() 