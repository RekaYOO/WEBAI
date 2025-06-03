import json
import logging
from pathlib import Path
from typing import Dict, Tuple, Union, List
import os
import pandas as pd

from loadgrade.neu_api import NEUAPI
from loadgrade.analyzer_api import AnalyzerAPI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class GradeLoader:
    """成绩加载和分析类"""
    
    def __init__(self, config_path: str, data_dir: str):
        """
        初始化成绩加载器
        
        Args:
            config_path: 配置文件路径
            data_dir: 数据存储目录路径
        """
        self.config_path = config_path
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        self.config = self._load_config()
        self.neu_api = NEUAPI(config_path, data_dir)
        self.analyzer = AnalyzerAPI(data_dir)
    
    def _load_config(self) -> Dict:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def login(self) -> Tuple[bool, str]:
        """
        登录统一身份认证系统
        
        Returns:
            Tuple[bool, str]: (是否成功, 消息)
        """
        success, result = self.neu_api.login()
        if success:
            logging.info("登录成功")
        else:
            logging.error(f"登录失败：{result}")
        return success, result
    
    def analyze_grades(self) -> Tuple[bool, Union[List[Dict], str]]:
        """
        分析成绩数据
        
        Returns:
            Tuple[bool, Union[List[Dict], str]]: (是否成功, 成绩数据列表或错误信息)
        """
        # 获取成绩
        success, result = self.neu_api.get_grades(save_to_file=False)
        if not success:
            return False, f"获取成绩失败：{result}"
        
        # 分析成绩
        success, grades_data = self.analyzer.analyze_grades(result)
        if not success:
            return False, f"分析成绩失败：{grades_data}"
        
        # 保存成绩数据
        output_path = self.data_dir / "grades.csv"
        if self.analyzer.save_grades_to_csv(grades_data, str(output_path)):
            logging.info(f"成绩数据已保存到：{output_path}")
            return True, grades_data
        else:
            return False, "保存成绩数据失败"
    
    def analyze_plan(self) -> Tuple[bool, str]:
        """
        分析培养计划
        
        Returns:
            Tuple[bool, str]: (是否成功, 清理后的HTML内容或错误信息)
        """
        # 获取培养计划
        success, result = self.neu_api.get_plan(save_to_file=False)
        if not success:
            return False, f"获取培养计划失败：{result}"
        
        # 分析培养计划
        success, plan_data = self.analyzer.analyze_plan(result)
        if not success:
            return False, f"分析培养计划失败：{plan_data}"
        
        # 保存培养计划数据
        output_path = self.data_dir / "plan_table.html"
        if self.analyzer.save_analysis_result(plan_data, str(output_path)):
            logging.info(f"培养计划数据已保存到：{output_path}")
            return True, plan_data
        else:
            return False, "保存培养计划数据失败"
    
    def analyze_plan_completion(self) -> Tuple[bool, str]:
        """
        分析培养计划完成情况
        
        Returns:
            Tuple[bool, str]: (是否成功, 清理后的HTML内容或错误信息)
        """
        # 获取培养计划完成情况
        success, result = self.neu_api.get_plan_completion(save_to_file=False)
        if not success:
            return False, f"获取培养计划完成情况失败：{result}"
        
        # 分析培养计划完成情况
        success, completion_data = self.analyzer.analyze_completion(result)
        if not success:
            return False, f"分析培养计划完成情况失败：{completion_data}"
        
        # 保存培养计划完成情况数据
        output_path = self.data_dir / "plan_completion_table.html"
        if self.analyzer.save_analysis_result(completion_data, str(output_path)):
            logging.info(f"培养计划完成情况数据已保存到：{output_path}")
            return True, completion_data
        else:
            return False, "保存培养计划完成情况数据失败"
    
    def read_analyzed_grades(self) -> Tuple[bool, Union[pd.DataFrame, str]]:
        """
        读取已分析的成绩数据
        
        Returns:
            Tuple[bool, Union[pd.DataFrame, str]]: (是否成功, 成绩数据DataFrame或错误信息)
        """
        grades_path = self.data_dir / "grades.csv"
        if not grades_path.exists():
            return False, "未找到成绩数据文件，请先运行成绩分析"
        
        try:
            grades_df = pd.read_csv(grades_path)
            logging.info(f"成功读取成绩数据，共 {len(grades_df)} 条记录")
            return True, grades_df
        except Exception as e:
            error_msg = f"读取成绩数据失败：{str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def read_analyzed_plan(self) -> Tuple[bool, Union[str, str]]:
        """
        读取已分析的培养计划数据
        
        Returns:
            Tuple[bool, Union[str, str]]: (是否成功, HTML内容或错误信息)
        """
        plan_path = self.data_dir / "plan_table.html"
        if not plan_path.exists():
            return False, "未找到培养计划数据文件，请先运行培养计划分析"
        
        try:
            with open(plan_path, 'r', encoding='utf-8') as f:
                plan_content = f.read()
            logging.info("成功读取培养计划数据")
            return True, plan_content
        except Exception as e:
            error_msg = f"读取培养计划数据失败：{str(e)}"
            logging.error(error_msg)
            return False, error_msg
    
    def read_analyzed_completion(self) -> Tuple[bool, Union[str, str]]:
        """
        读取已分析的培养计划完成情况数据
        
        Returns:
            Tuple[bool, Union[str, str]]: (是否成功, HTML内容或错误信息)
        """
        completion_path = self.data_dir / "plan_completion_table.html"
        if not completion_path.exists():
            return False, "未找到培养计划完成情况数据文件，请先运行培养计划完成情况分析"
        
        try:
            with open(completion_path, 'r', encoding='utf-8') as f:
                completion_content = f.read()
            logging.info("成功读取培养计划完成情况数据")
            return True, completion_content
        except Exception as e:
            error_msg = f"读取培养计划完成情况数据失败：{str(e)}"
            logging.error(error_msg)
            return False, error_msg

def main():
    """主函数：演示GradeLoader的使用"""
    print("开始加载和分析数据...")
    
    # 获取当前文件所在目录
    current_dir = Path(__file__).parent
    
    # 创建GradeLoader实例
    config_path = current_dir / "loadgrade" / "config.json"
    data_dir = current_dir / "data"
    
    if not config_path.exists():
        print(f"错误：配置文件不存在：{config_path}")
        return
        
    loader = GradeLoader(str(config_path), str(data_dir))
    
    # 登录
    success, result = loader.login()
    if not success:
        print(f"\n登录失败，程序终止：{result}")
        return
    
    # 分析成绩
    success, result = loader.analyze_grades()
    if success:
        print("\n成绩分析成功！")
        # 显示统计信息
        total_courses = len(result)
        print(f"总课程数: {total_courses}")
        if total_courses > 0:
            total_credits = sum(float(grade.get('学分', 0)) for grade in result if grade.get('学分', '').replace('.', '').isdigit())
            print(f"总学分: {total_credits:.1f}")
    else:
        print(f"\n成绩分析失败：{result}")
    
    # 分析培养计划
    success, result = loader.analyze_plan()
    if success:
        print("\n培养计划分析成功！")
    else:
        print(f"\n培养计划分析失败：{result}")
    
    # 分析培养计划完成情况
    success, result = loader.analyze_plan_completion()
    if success:
        print("\n培养计划完成情况分析成功！")
    else:
        print(f"\n培养计划完成情况分析失败：{result}")
    
    print("\n分析完成！")

if __name__ == "__main__":
    main() 