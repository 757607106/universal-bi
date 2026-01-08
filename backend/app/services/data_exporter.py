"""
数据导出服务 - 支持Excel/CSV格式导出
"""
import pandas as pd
import io
from datetime import datetime
from typing import List, Dict, Any
from app.core.logger import get_logger

logger = get_logger(__name__)


class DataExporter:
    """数据导出器"""
    
    @staticmethod
    def export_to_excel(
        data: List[Dict[str, Any]],
        columns: List[str],
        filename_prefix: str = "分析结果"
    ) -> tuple[bytes, str]:
        """
        导出数据为Excel格式
        
        Args:
            data: 数据列表
            columns: 列名列表
            filename_prefix: 文件名前缀
            
        Returns:
            tuple: (文件内容bytes, 文件名)
        """
        try:
            # 转换为DataFrame
            df = pd.DataFrame(data, columns=columns)
            
            # 创建BytesIO对象
            output = io.BytesIO()
            
            # 使用openpyxl引擎写入Excel
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='数据')
                
                # 获取工作表
                worksheet = writer.sheets['数据']
                
                # 自动调整列宽
                for idx, col in enumerate(df.columns):
                    max_length = max(
                        df[col].astype(str).apply(len).max(),
                        len(str(col))
                    )
                    # 设置列宽（最大50）
                    worksheet.column_dimensions[chr(65 + idx)].width = min(max_length + 2, 50)
            
            # 获取字节内容
            excel_bytes = output.getvalue()
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.xlsx"
            
            logger.info(
                "Data exported to Excel",
                rows=len(df),
                columns=len(df.columns),
                filename=filename,
                size_kb=len(excel_bytes) / 1024
            )
            
            return excel_bytes, filename
            
        except Exception as e:
            logger.error(f"Excel export failed: {e}", exc_info=True)
            raise ValueError(f"Excel导出失败: {str(e)}")
    
    @staticmethod
    def export_to_csv(
        data: List[Dict[str, Any]],
        columns: List[str],
        filename_prefix: str = "分析结果"
    ) -> tuple[bytes, str]:
        """
        导出数据为CSV格式
        
        Args:
            data: 数据列表
            columns: 列名列表
            filename_prefix: 文件名前缀
            
        Returns:
            tuple: (文件内容bytes, 文件名)
        """
        try:
            # 转换为DataFrame
            df = pd.DataFrame(data, columns=columns)
            
            # 转换为CSV（使用UTF-8 BOM以支持Excel正确打开中文）
            csv_content = df.to_csv(index=False, encoding='utf-8-sig')
            csv_bytes = csv_content.encode('utf-8-sig')
            
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{filename_prefix}_{timestamp}.csv"
            
            logger.info(
                "Data exported to CSV",
                rows=len(df),
                columns=len(df.columns),
                filename=filename,
                size_kb=len(csv_bytes) / 1024
            )
            
            return csv_bytes, filename
            
        except Exception as e:
            logger.error(f"CSV export failed: {e}", exc_info=True)
            raise ValueError(f"CSV导出失败: {str(e)}")
    
    @staticmethod
    def generate_filename(question: str, format: str = "xlsx") -> str:
        """
        根据问题生成合适的文件名
        
        Args:
            question: 用户问题
            format: 文件格式
            
        Returns:
            str: 文件名
        """
        # 提取关键词作为文件名
        import re
        
        # 清理特殊字符
        clean_question = re.sub(r'[^\w\u4e00-\u9fa5]', '_', question)
        clean_question = clean_question[:30]  # 限制长度
        
        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        filename = f"{clean_question}_{timestamp}.{format}"
        return filename

