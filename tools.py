import logging
from pathlib import Path
from typing import Tuple, Union, List, Dict
import pandas as pd

from backend.load import GradeLoader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# 获取当前文件所在目录
CURRENT_DIR = Path(__file__).parent
CONFIG_PATH = CURRENT_DIR / "backend" / "loadgrade" / "config.json"
DATA_DIR = CURRENT_DIR / "backend" / "data"

# 创建GradeLoader实例
loader = GradeLoader(str(CONFIG_PATH), str(DATA_DIR))

def analyze_gpa(use_cache: bool = True) -> Tuple[bool, Union[List[Dict], str]]:
    """
    分析绩点数据
    
    Args:
        use_cache: 是否使用缓存数据，如果为True且本地已有数据文件，则直接读取返回
        
    Returns:
        Tuple[bool, Union[List[Dict], str]]: (是否成功, 成绩数据列表或错误信息)
    """
    if use_cache:
        # 尝试读取已分析的成绩数据
        success, result = loader.read_analyzed_grades()
        if success:
            logging.info("使用缓存的成绩数据")
            return True, result
    
    # 登录
    success, result = loader.login()
    if not success:
        return False, f"登录失败：{result}"
    
    # 分析成绩
    return loader.analyze_grades()

def analyze_plan(use_cache: bool = True) -> Tuple[bool, Union[str, str]]:
    """
    分析培养计划
    
    Args:
        use_cache: 是否使用缓存数据，如果为True且本地已有数据文件，则直接读取返回
        
    Returns:
        Tuple[bool, Union[str, str]]: (是否成功, HTML内容或错误信息)
    """
    if use_cache:
        # 尝试读取已分析的培养计划数据
        success, result = loader.read_analyzed_plan()
        if success:
            logging.info("使用缓存的培养计划数据")
            return True, result
    
    # 登录
    success, result = loader.login()
    if not success:
        return False, f"登录失败：{result}"
    
    # 分析培养计划
    return loader.analyze_plan()

def analyze_plan_completion(use_cache: bool = True) -> Tuple[bool, Union[str, str]]:
    """
    分析培养计划完成情况
    
    Args:
        use_cache: 是否使用缓存数据，如果为True且本地已有数据文件，则直接读取返回
        
    Returns:
        Tuple[bool, Union[str, str]]: (是否成功, HTML内容或错误信息)
    """
    if use_cache:
        # 尝试读取已分析的培养计划完成情况数据
        success, result = loader.read_analyzed_completion()
        if success:
            logging.info("使用缓存的培养计划完成情况数据")
            return True, result
    
    # 登录
    success, result = loader.login()
    if not success:
        return False, f"登录失败：{result}"
    
    # 分析培养计划完成情况
    return loader.analyze_plan_completion()

def main():
    """示例用法"""
    print("开始分析数据...")
    
    # 分析绩点
    success, result = analyze_gpa(use_cache=True)
    if success:
        if isinstance(result, pd.DataFrame):
            print("\n绩点分析成功！")
            print(f"总课程数: {len(result)}")
            if len(result) > 0:
                total_credits = sum(float(grade.get('学分', 0)) for grade in result.to_dict('records') if grade.get('学分', '').replace('.', '').isdigit())
                print(f"总学分: {total_credits:.1f}")
    else:
        print(f"\n绩点分析失败：{result}")
    
    # 分析培养计划
    success, result = analyze_plan(use_cache=True)
    if success:
        print("\n培养计划分析成功！")
    else:
        print(f"\n培养计划分析失败：{result}")
    
    # 分析培养计划完成情况
    success, result = analyze_plan_completion(use_cache=True)
    if success:
        print("\n培养计划完成情况分析成功！")
    else:
        print(f"\n培养计划完成情况分析失败：{result}")
    
    print("\n分析完成！")

if __name__ == "__main__":
    main() 