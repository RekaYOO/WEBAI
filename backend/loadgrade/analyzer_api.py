import json
import logging
import csv
from pathlib import Path
from typing import Optional, List, Dict, Union, Tuple

from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class AnalyzerAPI:
    """培养计划分析器API类，提供清晰的接口供其他项目调用"""
    
    def __init__(self, data_dir: str):
        """
        初始化分析器API
        
        Args:
            data_dir: 数据存储目录路径
        """
        self.output_dir = Path(data_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
    
    def _find_target_table(self, soup: BeautifulSoup) -> Optional[BeautifulSoup]:
        """
        查找目标表格（以planInfoTable开头且后面有数字的表格）
        
        Args:
            soup: BeautifulSoup对象
            
        Returns:
            Optional[BeautifulSoup]: 找到的表格对象，如果没找到则返回None
        """
        # 查找所有表格
        all_tables = soup.find_all("table")
        logging.info(f"找到 {len(all_tables)} 个表格")
        
        # 查找目标表格（以planInfoTable开头且后面有数字的表格）
        target_tables = []
        for table in all_tables:
            table_id = table.get('id', '')
            if table_id.startswith('planInfoTable'):
                # 检查planInfoTable后面的部分是否为数字
                suffix = table_id[len('planInfoTable'):]
                if suffix and suffix.isdigit():
                    target_tables.append(table)
                    logging.info(f"找到目标表格: {table_id}")
        
        if not target_tables:
            logging.warning("未找到目标表格")
            return None
            
        # 如果找到多个目标表格，记录警告
        if len(target_tables) > 1:
            logging.warning(f"找到多个目标表格: {[table.get('id') for table in target_tables]}")
            
        return target_tables[0]  # 返回第一个匹配的表格
    
    def _clean_table(self, table: BeautifulSoup) -> BeautifulSoup:
        """
        清理表格，移除所有不必要的属性和脚本
        
        Args:
            table: 表格对象
            
        Returns:
            BeautifulSoup: 清理后的表格对象
        """
        # 移除所有script标签
        for script in table.find_all('script'):
            script.decompose()
            
        # 遍历所有行
        for row in table.find_all('tr'):
            # 检查行是否为空（只包含空白字符）
            if not row.get_text(strip=True):
                row.decompose()
                continue
                
            # 遍历行中的所有单元格
            for cell in row.find_all(['td', 'th']):
                # 移除所有属性
                attrs_to_remove = ['style', 'width', 'align', 'class', 'id', 'bgcolor']
                for attr in attrs_to_remove:
                    if attr in cell.attrs:
                        del cell[attr]
                
                # 清理单元格内容
                text = cell.get_text(strip=True)
                if not text or text == '&nbsp;':
                    cell.decompose()
                else:
                    # 移除所有空白行和回车符，只保留一个空格
                    text = ' '.join(text.split())
                    cell.string = text
        
        return table
    
    def analyze_plan(self, html_content: str) -> Tuple[bool, str]:
        """
        分析培养计划HTML内容
        
        Args:
            html_content: HTML内容字符串
            
        Returns:
            Tuple[bool, str]: (是否成功, 清理后的HTML内容或错误信息)
        """
        try:
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找目标表格
            target_table = self._find_target_table(soup)
            if not target_table:
                return False, "未找到目标表格"
            
            # 清理表格
            cleaned_table = self._clean_table(target_table)
            
            # 将HTML转换为字符串并移除所有回车和多余空格
            html_str = str(cleaned_table)
            html_str = ' '.join(html_str.split())
            
            return True, html_str
            
        except Exception as e:
            error_msg = f"分析培养计划失败: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def analyze_completion(self, html_content: str) -> Tuple[bool, str]:
        """
        分析培养计划完成情况HTML内容
        
        Args:
            html_content: HTML内容字符串
            
        Returns:
            Tuple[bool, str]: (是否成功, 清理后的HTML内容或错误信息)
        """
        try:
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找所有表格和chartView中的表格
            tables = soup.find_all('table')
            chart_view = soup.find('div', id='chartView')
            if chart_view:
                chart_tables = chart_view.find_all('table')
                tables.extend(chart_tables)
            
            if not tables:
                return False, "未找到培养计划完成情况表格"
            
            # 清理所有表格
            cleaned_tables = []
            for table in tables:
                cleaned_table = self._clean_table(table)
                cleaned_tables.append(cleaned_table)
            
            # 将所有清理后的表格连接成一个字符串
            html_str = ''.join(str(table) for table in cleaned_tables)
            html_str = ' '.join(html_str.split())
            
            return True, html_str
            
        except Exception as e:
            error_msg = f"分析培养计划完成情况失败: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def analyze_grades(self, html_content: str) -> Tuple[bool, Union[List[Dict], str]]:
        """
        分析成绩HTML内容
        
        Args:
            html_content: HTML内容字符串
            
        Returns:
            Tuple[bool, Union[List[Dict], str]]: (是否成功, 成绩数据列表或错误信息)
        """
        try:
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找成绩表格
            grid_div = soup.find('div', class_='grid')
            if not grid_div:
                return False, "未找到成绩表格"
            
            table = grid_div.find('table')
            if not table:
                return False, "未在grid div中找到表格"
            
            # 获取表头
            headers = []
            header_row = table.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all('th')]
            
            # 获取所有成绩数据
            grades_data = []
            for row in table.find_all('tr')[1:]:  # 跳过表头行
                cells = row.find_all('td')
                if not cells:
                    continue
                
                # 将单元格数据转换为字典
                grade_info = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        # 清理单元格文本
                        text = cell.get_text(strip=True)
                        text = ' '.join(text.split())  # 移除多余空白
                        grade_info[headers[i]] = text
                
                if grade_info:  # 只添加非空数据
                    grades_data.append(grade_info)
            
            return True, grades_data
            
        except Exception as e:
            error_msg = f"分析成绩数据失败: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def save_analysis_result(self, content: str, filename: str) -> bool:
        """
        保存分析结果到文件
        
        Args:
            content: 要保存的内容
            filename: 文件名
            
        Returns:
            bool: 是否保存成功
        """
        try:
            output_path = self.output_dir / filename
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logging.info(f"已保存分析结果到 {output_path}")
            return True
        except Exception as e:
            logging.error(f"保存分析结果失败: {str(e)}")
            return False
    
    def save_grades_to_csv(self, grades_data: List[Dict], filename: str = "grades.csv") -> bool:
        """
        将成绩数据保存为CSV文件
        
        Args:
            grades_data: 成绩数据列表
            filename: 文件名
            
        Returns:
            bool: 是否保存成功
        """
        try:
            if not grades_data:
                return False
                
            output_path = self.output_dir / filename
            with open(output_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=grades_data[0].keys())
                writer.writeheader()
                writer.writerows(grades_data)
            
            logging.info(f"已保存成绩数据到 {output_path}")
            return True
            
        except Exception as e:
            logging.error(f"保存成绩数据失败: {str(e)}")
            return False

def main():
    """示例用法"""
    api = AnalyzerAPI("backend/data")
    
    # 示例：分析培养计划
    with open("backend/data/plan.html", 'r', encoding='utf-8') as f:
        plan_html = f.read()
    success, result = api.analyze_plan(plan_html)
    if success:
        api.save_analysis_result(result, "plan_table.html")
    
    # 示例：分析培养计划完成情况
    with open("backend/data/plan_completion.html", 'r', encoding='utf-8') as f:
        completion_html = f.read()
    success, result = api.analyze_completion(completion_html)
    if success:
        api.save_analysis_result(result, "plan_completion_table.html")
    
    # 示例：分析成绩
    with open("backend/data/grades.html", 'r', encoding='utf-8') as f:
        grades_html = f.read()
    success, result = api.analyze_grades(grades_html)
    if success:
        api.save_grades_to_csv(result)

if __name__ == "__main__":
    main() 