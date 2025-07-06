import os
import glob
import json
from typing import List, Dict, Any, Optional

import pandas as pd
import numpy as np

try:
    import pdfplumber  # 用于解析 PDF
except ImportError:  # 如果环境里没有 pdfplumber，允许后续惰性导入
    pdfplumber = None  # type: ignore

import back_end.llm_api as llm_api


class AdmissionAgent:
    """招生智能体：负责加载数据集并提供给大模型可调用的分析工具。"""

    def __init__(self):
        # 预加载数据，避免反复 IO
        self._student_df: pd.DataFrame = self._load_student_data()
        self._arrangement_text: str = self._load_arrangement_text()
        # 推断并缓存列类型，便于后续智能分析
        self._column_types: Dict[str, str] = self._infer_column_types()

    # ------------------------------------------------------------------
    # 数据加载
    # ------------------------------------------------------------------

    @staticmethod
    def _load_student_data() -> pd.DataFrame:
        """加载考生信息表（*.xlsx）。"""
        # 先在当前工作目录查找，再在脚本所在目录查找
        excel_files = glob.glob("*考生信息表*.xlsx")
        if not excel_files:
            base_dir = os.path.dirname(__file__)
            excel_files = glob.glob(os.path.join(base_dir, "*考生信息表*.xlsx"))
        if not excel_files:
            raise FileNotFoundError("当前目录或 back_end 目录下未找到考生信息表 (*.xlsx)。")
        # 默认取第一个匹配文件
        df = pd.read_excel(excel_files[0])
        return df

    @staticmethod
    def _load_arrangement_text() -> str:
        """提取招生工作安排 PDF 的纯文本。若不存在或无法解析则返回空字符串。"""
        pdf_files = glob.glob("*招生工作安排*.pdf")
        if not pdf_files:
            base_dir = os.path.dirname(__file__)
            pdf_files = glob.glob(os.path.join(base_dir, "*招生工作安排*.pdf"))
        if not pdf_files:
            return ""
        if pdfplumber is None:
            # 延迟导入失败则提示
            print("提示：未安装 pdfplumber，无法解析 PDF，仅返回空文本。")
            return ""
        text_parts: List[str] = []
        with pdfplumber.open(pdf_files[0]) as pdf:
            for page in pdf.pages:
                try:
                    page_text = page.extract_text() or ""
                except Exception:
                    page_text = ""
                text_parts.append(page_text)
        return "\n".join(text_parts)

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _locate_student_row(self, student_id: str) -> pd.Series:
        """根据多种可能列名定位学生记录。"""
        possible_keys = [
            "考生号",
            "考号",
            "准考证号",
            "student_id",
            "ID",
        ]
        df = self._student_df
        for key in possible_keys:
            if key in df.columns:
                matches = df[df[key].astype(str) == str(student_id)]
                if not matches.empty:
                    return matches.iloc[0]
        raise ValueError(f"未找到 student_id={student_id} 的学生记录。")

    def _score_column(self) -> str:
        """尝试猜测成绩列名。"""
        for col in ["总分", "分数", "高考成绩", "score", "Score"]:
            if col in self._student_df.columns:
                return col
        raise ValueError("未能在考生信息表中找到成绩列，请确认列名。")

    # ------------------------------------------------------------------
    # 列类型推断与获取
    # ------------------------------------------------------------------

    def _infer_column_types(self) -> Dict[str, str]:
        """推断数据集中各列的语义类型（numeric / datetime / boolean / categorical / string）。"""
        df = self._student_df
        types: Dict[str, str] = {}

        for col in df.columns:
            s = df[col]

            # 直接使用 pandas dtype 判断
            if pd.api.types.is_numeric_dtype(s):
                types[col] = "numeric"
                continue

            # 尝试将对象列转为数值
            if s.dtype == "object":
                numeric_conv = pd.to_numeric(s.str.replace(",", "", regex=False), errors="coerce")
                numeric_ratio = numeric_conv.notna().mean()
                if numeric_ratio > 0.8:  # 大部分可成功转为数值
                    df[col] = numeric_conv  # 更新为数值列，便于后续操作
                    types[col] = "numeric"
                    continue

            if pd.api.types.is_datetime64_any_dtype(s):
                types[col] = "datetime"
            elif pd.api.types.is_bool_dtype(s):
                types[col] = "boolean"
            else:
                unique_ratio = s.nunique(dropna=False) / len(s)
                types[col] = "categorical" if unique_ratio < 0.05 else "string"

        return types

    def get_column_types(self) -> Dict[str, str]:
        """返回已推断的列类型映射。"""
        return self._column_types

    # ------------------------------------------------------------------
    # 通用数据分析函数（供 LLM 调用）
    # ------------------------------------------------------------------

    def describe_column(
        self,
        column_name: str,
        group_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """返回指定列的描述性统计信息，可选按另一列分组。

        参数说明：
        - column_name: 需统计的列名，可为数值型或分类型。
        - group_by: 若提供，则先按该列分组后分别计算 column_name 的描述统计。
        """
        if column_name not in self._student_df.columns:
            raise ValueError(f"在数据集中未找到列 {column_name}。")

        col_type = self._column_types.get(column_name, "string")
        df = self._student_df

        def _series_stats(s: pd.Series) -> Dict[str, Any]:
            if col_type == "numeric":
                desc = s.describe(percentiles=[0.25, 0.5, 0.75]).to_dict()
                rename_map = {"25%": "q1", "50%": "median", "75%": "q3"}
                return {rename_map.get(k, k): v for k, v in desc.items()}
            elif col_type == "datetime":
                return {"min": str(s.min()), "max": str(s.max()), "count": int(s.count())}
            else:
                value_counts = s.value_counts(dropna=False).to_dict()
                return {
                    "unique": int(s.nunique(dropna=False)),
                    "top_counts": value_counts,
                }

        result: Dict[str, Any] = {}

        if group_by and group_by in df.columns:
            grouped = df.groupby(group_by)[column_name]
            result["by_group"] = {str(g): _series_stats(series) for g, series in grouped}
        else:
            result["overall"] = _series_stats(df[column_name])

        return result

    def filter_students(
        self,
        filters: Dict[str, Any],
        sort_by: Optional[str] = None,
        ascending: bool = False,
        top_n: int = 20,
    ) -> List[Dict[str, Any]]:
        """按多条件过滤学生数据并返回结果。

        filters 的格式示例：
        {
            "省份": "江苏",
            "类别": ["物理类", "历史类"],
            "总分": {"gte": 600, "lte": 650}
        }
        数值范围键支持：gt/gte/lt/lte/min/max。
        """
        df = self._student_df.copy()

        for col, condition in filters.items():
            if col not in df.columns:
                raise ValueError(f"列 {col} 不存在于数据集中。")

            col_type = self._column_types.get(col, "string")

            if isinstance(condition, dict):
                if col_type == "numeric":
                    series = pd.to_numeric(df[col], errors="coerce")
                    if "gt" in condition or "min" in condition:
                        val = condition.get("gt", condition.get("min"))
                        df = df[series > float(val)]
                    if "gte" in condition:
                        df = df[series >= float(condition["gte"])]
                    if "lt" in condition or "max" in condition:
                        val = condition.get("lt", condition.get("max"))
                        df = df[series < float(val)]
                    if "lte" in condition:
                        df = df[series <= float(condition["lte"])]
                elif col_type == "datetime":
                    series = pd.to_datetime(df[col], errors="coerce")
                    if "after" in condition or "min" in condition:
                        val = pd.to_datetime(condition.get("after", condition.get("min")))
                        df = df[series > val]
                    if "on_or_after" in condition or "gte" in condition:
                        val = pd.to_datetime(condition.get("on_or_after", condition.get("gte")))
                        df = df[series >= val]
                    if "before" in condition or "max" in condition:
                        val = pd.to_datetime(condition.get("before", condition.get("max")))
                        df = df[series < val]
                    if "on_or_before" in condition or "lte" in condition:
                        val = pd.to_datetime(condition.get("on_or_before", condition.get("lte")))
                        df = df[series <= val]
                else:
                    # 对分类/字符串列使用正则或完全匹配
                    if "regex" in condition:
                        df = df[df[col].astype(str).str.contains(condition["regex"], na=False, regex=True)]
            elif isinstance(condition, list):
                df = df[df[col].isin(condition)]
            else:
                df = df[df[col] == condition]

        if sort_by and sort_by in df.columns:
            df = df.sort_values(by=sort_by, ascending=ascending)

        return df.head(top_n).to_dict(orient="records")

    # ------------------------------------------------------------------
    # 工具函数（供 LLM 调用）
    # ------------------------------------------------------------------

    def get_student_info(self, student_id: str) -> Dict[str, Any]:
        """根据 student_id 返回该考生的完整信息。"""
        row = self._locate_student_row(student_id)
        return row.to_dict()

    def recommend_major(self, student_id: str, top_n: int = 3) -> Dict[str, Any]:
        """基于成绩简单推荐专业。

        当前实现示例：
        1. 若考生表包含 "专业意向" 列，则直接返回其意向。
        2. 否则将考生成绩与全体分数分位进行比较，并输出可选专业类别建议（示例）。
        """
        row = self._locate_student_row(student_id)
        response: Dict[str, Any] = {"student_id": student_id}

        # 直接返回考生已有的专业意向
        for col in ["专业意向", "第一志愿", "志愿专业"]:
            if col in row.index and pd.notna(row[col]):
                response["recommended_majors"] = str(row[col]).split("/ ")
                response["reason"] = "已根据考生填报的专业意向进行返回。"
                return response

        # 若无明确意向，则基于成绩给出示例推荐
        score_col = self._score_column()
        student_score = float(row[score_col])
        scores = self._student_df[score_col].astype(float)
        percentile = (scores < student_score).mean() * 100  # 计算分位

        if percentile >= 90:
            candidate = ["计算机科学与技术", "信息安全", "人工智能"]
        elif percentile >= 70:
            candidate = ["电子信息工程", "软件工程", "自动化"]
        elif percentile >= 50:
            candidate = ["材料科学与工程", "环境科学", "经济学"]
        else:
            candidate = ["公共管理", "汉语言文学", "市场营销"]

        response["recommended_majors"] = candidate[:top_n]
        response["reason"] = f"基于高考成绩分位（约 {percentile:.1f}%）给出的示例推荐。"
        return response

    def list_top_students_for_major(self, major_keyword: str, top_n: int = 10) -> List[Dict[str, Any]]:
        """根据志愿关键词筛选并返回成绩最高的前 N 名学生。"""
        score_col = self._score_column()
        df = self._student_df.copy()

        # 根据关键字过滤 "专业意向"/"志愿专业" 等列
        possible_cols = ["专业意向", "第一志愿", "志愿专业"]
        filter_mask = pd.Series([False] * len(df))
        for col in possible_cols:
            if col in df.columns:
                filter_mask |= df[col].astype(str).str.contains(major_keyword, na=False)

        if filter_mask.any():
            df = df[filter_mask]
        # 若无匹配，则直接取全体

        df_sorted = df.sort_values(by=score_col, ascending=False).head(top_n)
        return df_sorted.to_dict(orient="records")

    # ------------------------------------------------------------------
    # 构建工具描述 & 运行对话
    # ------------------------------------------------------------------

    def build_tools_and_mapper(self):
        """返回 (tools, function_mapper)。"""
        tools: List[Dict[str, Any]] = [
            {
                "type": "function",
                "function": {
                    "name": "get_student_info",
                    "description": "根据学生 ID/考号/准考证号获取学生完整信息。返回字段取决于表格结构。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "学生在考生信息表中的唯一标识，如考生号。",
                            }
                        },
                        "required": ["student_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "recommend_major",
                    "description": "根据学生信息及招生规则返回推荐专业列表。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "student_id": {
                                "type": "string",
                                "description": "学生在考生信息表中的唯一标识，如考生号。",
                            },
                            "top_n": {
                                "type": "integer",
                                "description": "返回推荐专业数量，默认 3。",
                                "default": 3,
                            },
                        },
                        "required": ["student_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "list_top_students_for_major",
                    "description": "根据专业关键词筛选志愿并按成绩排序，返回成绩最高的前 N 名学生。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "major_keyword": {
                                "type": "string",
                                "description": "专业名称或关键词，例如 '计算机'。",
                            },
                            "top_n": {
                                "type": "integer",
                                "description": "返回学生数量，默认 10。",
                                "default": 10,
                            },
                        },
                        "required": ["major_keyword"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "describe_column",
                    "description": "返回指定列（如成绩、省份等）的描述性统计信息，可按另一列分组。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column_name": {
                                "type": "string",
                                "description": "需要统计的列名，例如 '总分'。",
                            },
                            "group_by": {
                                "type": "string",
                                "description": "可选，按此列分组后分别统计，如 '省份'，默认为空。",
                            },
                        },
                        "required": ["column_name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "filter_students",
                    "description": "根据多重过滤条件筛选学生，并按指定列排序返回前 N 条记录。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filters": {
                                "type": "object",
                                "description": "过滤条件，键为列名，值可为单值、列表或范围对象。",
                            },
                            "sort_by": {
                                "type": "string",
                                "description": "排序依据列名，例如 '总分'。若为空则不排序。",
                            },
                            "ascending": {
                                "type": "boolean",
                                "description": "排序升序或降序，默认 False（降序）。",
                                "default": False
                            },
                            "top_n": {
                                "type": "integer",
                                "description": "返回记录数，默认 20。",
                                "default": 20
                            },
                        },
                        "required": ["filters"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_column_types",
                    "description": "返回招生信息表中各列的推断类型（numeric/datetime/boolean/categorical/string）。",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
        ]

        function_mapper = {
            "get_student_info": self.get_student_info,
            "recommend_major": self.recommend_major,
            "list_top_students_for_major": self.list_top_students_for_major,
            "describe_column": self.describe_column,
            "filter_students": self.filter_students,
            "get_column_types": self.get_column_types,
        }
        return tools, function_mapper


# ----------------------------------------------------------------------
# 运行入口
# ----------------------------------------------------------------------

def run_chat() -> None:
    """CLI 入口：启动与大模型的交互式对话。"""
    agent = AdmissionAgent()
    tools, function_mapper = agent.build_tools_and_mapper()

    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "你是南京大学招生助手，需要根据招生工作安排与考生信息表来分析学生与专业的匹配。"
                "在需要更精确数据时，可通过已注册的工具函数获取结构化信息。"
            ),
        }
    ]

    print("欢迎使用南京大学招生智能体，输入问题，输入 exit 退出。")
    while True:
        user_query = input(">> ").strip()
        if user_query.lower() in {"exit", "quit", "bye"}:
            print("再见！")
            break

        messages.append({"role": "user", "content": user_query})

        # 调用大模型，内部会自动迭代处理工具调用
        reply, messages = llm_api.llm_action(messages, tools, function_mapper)
        print("\n[助手]", reply, "\n", flush=True)


if __name__ == "__main__":
    # 若直接执行 agent.py，则启动对话
    run_chat()
