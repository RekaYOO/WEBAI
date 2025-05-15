import logging
from pathlib import Path
from neu_api import NEUAPI
from analyzer_api import AnalyzerAPI

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def ensure_output_dir():
    """确保输出目录存在"""
    # 获取当前文件所在目录
    current_dir = Path(__file__).parent
    output_dir = current_dir.parent / "data"
    output_dir.mkdir(exist_ok=True)
    return output_dir

def main():
    """主函数：演示API的使用"""
    print("开始演示API使用...")
    
    # 获取当前文件所在目录
    current_dir = Path(__file__).parent
    
    # 确保输出目录存在
    output_dir = ensure_output_dir()
    
    # 创建API实例
    config_path = current_dir / "config.json"
    if not config_path.exists():
        print(f"错误：配置文件不存在：{config_path}")
        return
        
    neu_api = NEUAPI(str(config_path), str(output_dir))
    analyzer = AnalyzerAPI(str(output_dir))
    
    # 登录
    success, message = neu_api.login()
    print(f"登录结果: {message}")
    
    if success:
        # 获取成绩
        success, result = neu_api.get_grades()
        if success:
            print("获取成绩成功")
            # 分析成绩
            success, grades_data = analyzer.analyze_grades(result['data'])
            if success:
                print("分析成绩成功")
                analyzer.save_grades_to_csv(grades_data)
            else:
                print(f"分析成绩失败：{grades_data}")
        else:
            print(f"获取成绩失败：{result}")
        
        # 获取培养计划
        success, result = neu_api.get_plan()
        if success:
            print("获取培养计划成功")
            # 分析培养计划
            success, plan_data = analyzer.analyze_plan(result['data'])
            if success:
                print("分析培养计划成功")
                analyzer.save_analysis_result(plan_data, "plan_table.html")
            else:
                print(f"分析培养计划失败：{plan_data}")
        else:
            print(f"获取培养计划失败：{result}")
        
        # 获取培养计划完成情况
        success, result = neu_api.get_plan_completion()
        if success:
            print("获取培养计划完成情况成功")
            # 分析培养计划完成情况
            success, completion_data = analyzer.analyze_completion(result['data'])
            if success:
                print("分析培养计划完成情况成功")
                analyzer.save_analysis_result(completion_data, "plan_completion_table.html")
            else:
                print(f"分析培养计划完成情况失败：{completion_data}")
        else:
            print(f"获取培养计划完成情况失败：{result}")
    
    print("\n演示完成！")
    print("\n生成的文件:")
    print(f"1. {output_dir}/plan_table.html - 培养计划表格")
    print(f"2. {output_dir}/plan_completion_table.html - 培养计划完成情况表格")
    print(f"3. {output_dir}/grades.csv - 成绩数据")

if __name__ == "__main__":
    main() 