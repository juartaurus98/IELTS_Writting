from typing import List, Optional
import json
import base64
import io
from google import genai
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

from .models import GenerateTasksResponse, GradeResponse, CriterionScore


class GeminiClient:
    """Client thao tác với Google Gemini cho IELTS Writing."""

    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash") -> None:
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate_writing_tasks(self) -> GenerateTasksResponse:
        """Sinh hai đề: Task 1 và Task 2 theo chuẩn IELTS Writing."""
        sys_t1 = (
            "You are an IELTS Writing examiner. Generate ONE IELTS Writing Task 1 prompt (Academic). "
            "The task should require describing a graph/chart/table/process/map. "
            "Be specific about the visual type and include key details in the prompt. "
            "Output ONLY the prompt text in English."
        )
        sys_t1_chart = (
            "Generate detailed chart/graph/table data that matches the Task 1 prompt above. "
            "If the task is about a graph/chart/table, provide the actual data in VALID JSON format. "
            "JSON structure examples:\n"
            "- Single series bar/line chart: {\"years\": [2018, 2019, 2020], \"values\": [100, 150, 200], \"ylabel\": \"Sales (millions)\", \"title\": \"Sales Over Time\"}\n"
            "- Multiple series bar chart (comparison): {\"chart_type\": \"bar\", \"categories\": [\"A\", \"B\", \"C\"], \"series\": [{\"label\": \"1990\", \"values\": [100, 150, 200]}, {\"label\": \"2010\", \"values\": [120, 180, 250]}], \"ylabel\": \"Units\", \"title\": \"Comparison Chart\"}\n"
            "- Pie chart: {\"labels\": [\"A\", \"B\", \"C\"], \"values\": [30, 40, 30], \"title\": \"Distribution\"}\n"
            "- Table: {\"data\": [[\"Item\", \"Value\"], [\"A\", 100], [\"B\", 200]], \"title\": \"Data Table\"}\n"
            "Include: chart_type, labels/categories, values/series, units, time periods. "
            "For comparison charts (multiple years/periods), use 'series' array with each series having 'label' and 'values'. "
            "If the task is about a process/map, provide a detailed step-by-step description in text format. "
            "Output ONLY valid JSON wrapped in ```json code block, or plain text if process/map."
        )
        sys_t2 = (
            "You are an IELTS Writing examiner. Generate ONE IELTS Writing Task 2 prompt. "
            "It should be realistic, contemporary, and clearly phrased. "
            "Output ONLY the prompt text in English."
        )
        resp1 = self.client.models.generate_content(model=self.model_name, contents=sys_t1)
        t1 = _response_to_text(resp1).strip()
        
        # Sinh dữ liệu biểu đồ phù hợp với đề Task 1
        combined_for_chart = f"{sys_t1}\n\nGenerated prompt:\n{t1}\n\n{sys_t1_chart}"
        resp1_chart = self.client.models.generate_content(model=self.model_name, contents=combined_for_chart)
        chart_data = _response_to_text(resp1_chart).strip()
        
        resp2 = self.client.models.generate_content(model=self.model_name, contents=sys_t2)
        t2 = _response_to_text(resp2).strip()
        
        # Sinh hình ảnh biểu đồ từ dữ liệu
        chart_image = None
        if chart_data:
            chart_image = self._generate_chart_image(chart_data, t1)
        
        return GenerateTasksResponse(
            task1=t1, 
            task2=t2, 
            task1_chart_data=chart_data if chart_data else None,
            task1_chart_image=chart_image
        )
    
    def _generate_chart_image(self, chart_data: str, prompt: str) -> Optional[str]:
        """Tạo hình ảnh biểu đồ từ dữ liệu JSON bằng matplotlib."""
        try:
            # Parse JSON từ chart_data
            data_dict = _extract_json_dict(chart_data)
            if not data_dict:
                # Nếu không parse được JSON, thử tìm JSON trong text
                try:
                    json_match = json.loads(chart_data) if chart_data.strip().startswith('{') else None
                    if json_match:
                        data_dict = json_match
                    else:
                        return None
                except Exception:
                    return None
            
            # Xác định loại biểu đồ từ data hoặc prompt
            chart_type = data_dict.get('chart_type', '').lower() if isinstance(data_dict, dict) else ''
            if not chart_type:
                prompt_lower = prompt.lower()
                if 'line' in prompt_lower or 'graph' in prompt_lower:
                    chart_type = 'line'
                elif 'bar' in prompt_lower or 'column' in prompt_lower:
                    chart_type = 'bar'
                elif 'pie' in prompt_lower or 'circular' in prompt_lower:
                    chart_type = 'pie'
                elif 'table' in prompt_lower:
                    chart_type = 'table'
                else:
                    chart_type = 'bar'  # Default
            
            # Tạo biểu đồ với matplotlib
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if chart_type == 'table':
                # Hiển thị bảng
                if isinstance(data_dict, dict) and 'data' in data_dict:
                    table_data = data_dict['data']
                    if isinstance(table_data, list):
                        ax.axis('tight')
                        ax.axis('off')
                        table = ax.table(cellText=table_data, loc='center', cellLoc='center')
                        table.auto_set_font_size(False)
                        table.set_fontsize(9)
                        table.scale(1.2, 1.5)
                    else:
                        return None
                else:
                    return None
                    
            elif chart_type == 'pie':
                # Biểu đồ tròn
                if 'labels' in data_dict and 'values' in data_dict:
                    ax.pie(data_dict['values'], labels=data_dict['labels'], autopct='%1.1f%%', startangle=90)
                else:
                    return None
                    
            elif chart_type == 'bar':
                # Xử lý bar chart với nhiều series
                if 'series' in data_dict and 'categories' in data_dict:
                    cats = data_dict['categories']
                    series_list = data_dict['series']
                    ylabel = data_dict.get('ylabel', 'Value')
                    
                    # Tạo grouped bar chart
                    x = np.arange(len(cats))
                    width = 0.35 if len(series_list) == 2 else 0.8 / len(series_list)
                    offset = -width * (len(series_list) - 1) / 2
                    
                    for i, series in enumerate(series_list):
                        label = series.get('label', f'Series {i+1}')
                        values = series.get('values', [])
                        if len(values) == len(cats):
                            ax.bar(x + offset + i * width, values, width, label=label)
                    
                    ax.set_xlabel('Country' if 'country' in str(cats).lower() else 'Category')
                    ax.set_ylabel(ylabel)
                    ax.set_title(data_dict.get('title', 'Bar Chart'))
                    ax.set_xticks(x)
                    ax.set_xticklabels(cats)
                    ax.legend()
                    
                elif 'categories' in data_dict and 'values' in data_dict:
                    cats = data_dict['categories']
                    vals = data_dict['values']
                    ax.bar(cats, vals)
                    ax.set_xlabel(data_dict.get('xlabel', 'Category'))
                    ax.set_ylabel(data_dict.get('ylabel', 'Value'))
                elif 'years' in data_dict and 'values' in data_dict:
                    ax.bar(data_dict['years'], data_dict['values'])
                    ax.set_xlabel('Year')
                    ax.set_ylabel(data_dict.get('ylabel', 'Value'))
                else:
                    return None
                    
            else:  # line chart
                # Biểu đồ đường
                if 'years' in data_dict and 'values' in data_dict:
                    ax.plot(data_dict['years'], data_dict['values'], marker='o')
                    ax.set_xlabel('Year')
                    ax.set_ylabel(data_dict.get('ylabel', 'Value'))
                elif 'x' in data_dict and 'y' in data_dict:
                    ax.plot(data_dict['x'], data_dict['y'], marker='o')
                    ax.set_xlabel(data_dict.get('xlabel', 'X'))
                    ax.set_ylabel(data_dict.get('ylabel', 'Y'))
                elif 'categories' in data_dict and 'values' in data_dict:
                    ax.plot(data_dict['categories'], data_dict['values'], marker='o')
                    ax.set_xlabel('Category')
                    ax.set_ylabel(data_dict.get('ylabel', 'Value'))
                else:
                    return None
            
            # Set title
            title = data_dict.get('title', 'Chart')
            ax.set_title(title, fontsize=12, fontweight='bold')
            
            # Rotate x-axis labels if needed
            if chart_type in ['bar', 'line']:
                plt.xticks(rotation=45, ha='right')
            
            plt.tight_layout()
            
            # Chuyển đổi thành base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
            buf.seek(0)
            image_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            
            return image_base64
        except Exception as e:  # noqa: BLE001 - best effort
            # Nếu không thể tạo biểu đồ, trả về None
            return None
    def grade_essay(self, prompt: str, essay: str, task_type: str = "task2") -> GradeResponse:
        """Chấm bài viết theo band descriptors công bố cho Task 1/Task 2."""
        if task_type == "task1":
            descriptors_header = (
                "Evaluate IELTS Writing Task 1 using the public band descriptors.\n"
                "Criteria names: Task Achievement, Coherence and Cohesion, Lexical Resource, Grammatical Range and Accuracy.\n"
                "Task 1 specific requirements: write at least 150 words; provide a clear overview summarising main trends, differences or stages; describe significant data accurately; do not include personal opinions or arguments; maintain a formal tone.\n\n"
                "Band descriptors summary (public version):\n"
                "9: fully satisfies all requirements; fully developed response; cohesion attracts no attention; skilful paragraphing; wide vocabulary with natural, sophisticated control (only rare slips); wide range of structures with full flexibility and accuracy (rare slips).\n"
                "8: covers all requirements sufficiently; highlights/illustrates key features appropriately; logical sequencing; manages cohesion well; sufficient and appropriate paragraphing; wide vocabulary fluently and flexibly (precise meanings); skilful uncommon items (occasional inaccuracies); rare spelling/formation errors; wide range of structures; majority error-free; very occasional errors.\n"
                "7: covers requirements; clear overview of trends/differences/stages; clearly presents and highlights key features (could be more fully extended); logical organisation with clear progression; range of cohesive devices (some under/over-use); sufficient vocabulary for flexibility/precision; some less common items with awareness of style/collocation; occasional lexical errors; variety of complex structures; frequent error-free sentences; good control with a few errors.\n"
                "6: addresses requirements; overview with appropriately selected information; adequately highlights key features (some details may be irrelevant/inaccurate); coherent arrangement with clear overall progression; cohesive devices used but cohesion may be faulty/mechanical; referencing may be unclear; adequate range of vocabulary with attempts at less common items (some inaccuracy); some spelling/formation errors not impeding communication; mix of simple/complex forms; some grammar/punctuation errors rarely reducing communication.\n"
                "5: generally addresses task (format may be inappropriate); recounts detail mechanically with no clear overview; inadequately covers key features (focus on details); some organisation but lack of overall progression; inadequate/inaccurate/over-use of cohesive devices; repetitive due to lack of referencing/substitution; limited vocabulary (minimally adequate) with noticeable errors causing some difficulty; limited range of structures; attempts complex forms but less accurate; frequent grammatical/punctuation errors causing some difficulty.\n"
                "4: attempts task but does not cover all key features (format may be inappropriate); may confuse features with detail; parts unclear/irrelevant/repetitive/inaccurate; ideas not arranged coherently and no clear progression; some basic cohesive devices (inaccurate/repetitive); only basic vocabulary (repetitive/inappropriate); limited control of word formation/spelling with errors causing strain; very limited range of structures with rare subordination; some accurate structures but errors predominate; punctuation often faulty.\n"
                "3: fails to address task (may be misunderstood); limited ideas largely irrelevant/repetitive; ideas not organised; very limited cohesive devices not indicating logical relations; very limited words/expressions with very limited control (errors may severely distort); attempts sentence forms but errors predominate and distort meaning.\n"
                "2: answer barely related to task; very little control of organisational features; extremely limited vocabulary with essentially no control of formation/spelling; cannot use sentence forms except memorised phrases.\n"
                "1: answer completely unrelated; fails to communicate any message; only isolated words; cannot use sentence forms at all.\n"
                "0: does not attend/attempt or totally memorised response."
            )
        else:
            descriptors_header = (
                "Evaluate IELTS Writing Task 2 using the public band descriptors.\n"
                "Criteria names: Task Response, Coherence and Cohesion, Lexical Resource, Grammatical Range and Accuracy.\n\n"
                "Band descriptors summary (public version):\n"
                "9: fully addresses all parts; fully developed position with relevant, fully extended and well supported ideas; cohesion attracts no attention; skilful paragraphing; wide vocabulary with natural, sophisticated control (rare slips); wide range of structures with full flexibility and accuracy (rare slips).\n"
                "8: sufficiently addresses all parts; well-developed response with relevant, extended and supported ideas; logical sequencing; manages cohesion well; sufficient/appropriate paragraphing; wide vocabulary fluently and flexibly to convey precise meanings; skilful uncommon items (occasional inaccuracies); rare spelling/formation errors; wide range of structures; majority error-free; very occasional errors.\n"
                "7: addresses all parts; clear position throughout; presents, extends and supports main ideas (may over-generalise or supporting ideas lack focus); logical organisation with clear progression; range of cohesive devices (some under/over-use); clear central topic within each paragraph; sufficient vocabulary allowing some flexibility and precision; less common items with some awareness of style/collocation; occasional lexical errors; variety of complex structures; frequent error-free sentences; good control with a few errors.\n"
                "6: addresses all parts (some parts more fully covered); relevant position though conclusions may be unclear/repetitive; relevant main ideas but some inadequately developed/unclear; coherent arrangement with clear overall progression; cohesive devices used but cohesion may be faulty/mechanical; referencing not always clear/appropriate; paragraphing used but not always logical; adequate vocabulary with attempts at less common items (some inaccuracy); some spelling/formation errors not impeding communication; mix of simple/complex forms; some grammar/punctuation errors rarely reducing communication.\n"
                "5: addresses the task only partially (format may be inappropriate); expresses a position but development not always clear and no conclusions; some main ideas limited and insufficiently developed with possible irrelevant detail; some organisation but lack of overall progression; inadequate/inaccurate/over-use of cohesive devices; repetitive due to lack of referencing/substitution; may not write in paragraphs or paragraphing inadequate; limited vocabulary (minimally adequate) with noticeable errors causing some difficulty; limited range of structures; attempts complex forms but less accurate than simple; frequent grammatical/punctuation errors causing some difficulty.\n"
                "4: minimal or tangential response (format may be inappropriate); unclear position; some main ideas difficult to identify, repetitive/irrelevant/unsupported; ideas not arranged coherently with no clear progression; some basic cohesive devices (inaccurate/repetitive); no/poor paragraphing; only basic vocabulary (repetitive/inappropriate) with limited control of formation/spelling (errors may cause strain); very limited range of structures with only rare subordination; some accurate structures but errors predominate; punctuation often faulty.\n"
                "3: does not adequately address any part; no clear position; few ideas largely undeveloped/irrelevant; ideas not organised logically; very limited cohesive devices not indicating logical relations; very limited words/expressions with very limited control (errors may severely distort); attempts sentence forms but errors predominate and distort meaning.\n"
                "2: barely responds; no position; may attempt 1-2 ideas with no development; very little control of organisational features; extremely limited vocabulary with essentially no control of formation/spelling; cannot use sentence forms except memorised phrases.\n"
                "1: completely unrelated; fails to communicate any message; only isolated words; cannot use sentence forms at all.\n"
                "0: does not attend/attempt or totally memorised response."
            )

        # Chính sách chấm nghiêm khắc hơn
        strict_policy = (
            "Scoring policy (be conservative):\n"
            "- Use only 0.5 increments for all bands.\n"
            "- When uncertain between two adjacent bands, choose the LOWER band.\n"
            "- Provide 1-2 concrete evidence snippets in each criterion comment (what exactly is good/bad).\n"
            "- Overall band MUST be the arithmetic mean of the four criteria bands, rounded DOWN to the nearest 0.5.\n"
            "- If word count is below the minimum, apply penalties:\n"
            "  * Task 1 (<150 words): cap Task Achievement at 5.0 and overall at 5.5.\n"
            "  * Task 2 (<250 words): cap Task Response at 5.0 and overall at 5.5.\n"
        )

        # Hướng dẫn chi tiết theo từng tiêu chí (khác biệt giữa Task 1 và Task 2 ở tiêu chí đầu)
        if task_type == "task1":
            criterion_guidance = (
                "Criterion-specific guidance (use exact names):\n"
                "- Task Achievement (TA):\n"
                "  Assess: clear overview; accurate selection/synthesis of key features; relevance; no opinions.\n"
                "  Penalise: missing/unclear overview; misreported/comparative errors; focusing on trivial details; irrelevant content.\n"
                "- Coherence and Cohesion (CC):\n"
                "  Assess: logical progression; effective paragraphing; clear referencing/substitution; varied cohesive devices without mechanical feel.\n"
                "  Penalise: illogical sequence; mechanical/overused devices; unclear referencing; weak or absent paragraphing.\n"
                "- Lexical Resource (LR):\n"
                "  Assess: range; precision; appropriacy for visual description; paraphrasing; control of word formation/spelling.\n"
                "  Penalise: repetition; inaccurate word choice/collocation; spelling/formation errors that strain comprehension.\n"
                "- Grammatical Range and Accuracy (GRA):\n"
                "  Assess: variety (simple+complex); clause control; tense/aspect accuracy; punctuation.\n"
                "  Penalise: frequent errors; limited range; faulty punctuation causing difficulty.\n"
                "Score each criterion INDEPENDENTLY using 0.5 steps.\n"
                "Use the EXACT criterion names above in the JSON.\n"
            )
        else:
            criterion_guidance = (
                "Criterion-specific guidance (use exact names):\n"
                "- Task Response (TR):\n"
                "  Assess: addresses ALL parts; clear/consistent position; sufficient development/support of main ideas; relevance.\n"
                "  Penalise: partially addressed task; unclear/inconsistent position; underdeveloped/unsupported ideas; off-topic content.\n"
                "- Coherence and Cohesion (CC):\n"
                "  Assess: logical progression; effective paragraphing; clear referencing/substitution; varied cohesive devices without mechanical feel.\n"
                "  Penalise: illogical sequence; mechanical/overused devices; unclear referencing; weak or absent paragraphing.\n"
                "- Lexical Resource (LR):\n"
                "  Assess: range; precision; appropriacy and style; paraphrasing; control of word formation/spelling.\n"
                "  Penalise: repetition; inaccurate word choice/collocation; spelling/formation errors that cause difficulty.\n"
                "- Grammatical Range and Accuracy (GRA):\n"
                "  Assess: variety (simple+complex); clause control; tense/aspect accuracy; punctuation.\n"
                "  Penalise: frequent errors; limited range; faulty punctuation causing difficulty.\n"
                "Score each criterion INDEPENDENTLY using 0.5 steps.\n"
                "Use the EXACT criterion names above in the JSON.\n"
            )

        process_guidance = (
            "Scoring process (follow strictly):\n"
            "1) Score each criterion independently using the criterion-specific guidance above.\n"
            "2) Use ONLY 0.5 increments; if uncertain, choose the LOWER band.\n"
            "3) Compute overall as the arithmetic mean of the four criterion bands, rounded DOWN to the nearest 0.5.\n"
            "4) Apply word-count penalties and caps as specified.\n"
        )

        grading_instructions = (
            f"You are an official IELTS Writing examiner. {descriptors_header}\n\n{strict_policy}\n{criterion_guidance}\n{process_guidance}\nReturn a JSON with: \n"
            "- overall_band (float, 0.0-9.0)\n"
            "- criteria (array of {name, band, comment}) with the criteria above\n"
            "- feedback (string) concise summary of strengths and weaknesses\n"
            "- suggestions (string) concrete, actionable improvements\n"
            "- improved_version (string) a polished version that preserves meaning and structure\n"
            "Use Vietnamese for feedback, suggestions, and improved_version."
        )

        # Thêm thống kê số từ để mô hình tham chiếu khi áp dụng phạt
        try:
            word_count = len((essay or "").split())
        except Exception:  # noqa: BLE001 - defensive
            word_count = 0

        user_payload = (
            f"PROMPT:\n{prompt}\n\nWORD_COUNT:{word_count}\nTASK_TYPE:{task_type}\n\nESSAY:\n{essay}\n\n"
            "Please be fair, consistent, and conservative as per the policy."
        )

        contents = f"{grading_instructions}\n\n{user_payload}"
        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=contents,
        )

        text = _response_to_text(resp) or "{}"
        data = _extract_json_dict(text)

        # Chuẩn hóa band theo bước 0.5 và áp dụng các giới hạn tổng hợp ở backend (best-effort)
        def _round_down_to_half(x: float) -> float:
            try:
                return max(0.0, (int(x * 2) // 1) / 2)
            except Exception:
                return 0.0

        # Tên tiêu chí theo từng task để mapping đúng (Task 1 vs Task 2)
        if task_type == "task1":
            expected_names = [
                "Task Achievement",
                "Coherence and Cohesion",
                "Lexical Resource",
                "Grammatical Range and Accuracy",
            ]
            min_words = 150
            cap_criterion = "Task Achievement"
        else:
            expected_names = [
                "Task Response",
                "Coherence and Cohesion",
                "Lexical Resource",
                "Grammatical Range and Accuracy",
            ]
            min_words = 250
            cap_criterion = "Task Response"

        try:
            word_count = len((essay or "").split())
        except Exception:
            word_count = 0

        criteria_items: List[CriterionScore] = []
        raw_criteria = data.get("criteria", []) or []
        # Duy trì thứ tự tiêu chí kỳ vọng nếu có thể
        def _key_order(item: dict) -> int:
            try:
                name = str(item.get("name", ""))
                return expected_names.index(name) if name in expected_names else 999
            except Exception:
                return 999

        raw_criteria_sorted = sorted(raw_criteria, key=_key_order)
        for item in raw_criteria_sorted:
            criteria_items.append(
                CriterionScore(
                    name=str(item.get("name", "")),
                    band=float(item.get("band", 0)),
                    comment=str(item.get("comment", "")),
                )
            )

        # Áp dụng chuẩn hóa band 0.5 và phạt thiếu từ ở backend
        capped_overall = None
        rounded_bands: List[float] = []
        for c in criteria_items:
            rounded = _round_down_to_half(float(getattr(c, "band", 0)))
            c.band = rounded
            rounded_bands.append(rounded)

        if word_count < min_words and criteria_items:
            # Cap tiêu chí chính tối đa 5.0 nếu thiếu từ
            for c in criteria_items:
                if c.name == cap_criterion:
                    c.band = min(c.band, 5.0)
            capped_overall = 5.5

        # Tính overall = trung bình, làm tròn xuống 0.5
        if criteria_items:
            avg = sum([c.band for c in criteria_items]) / len(criteria_items)
            overall = _round_down_to_half(avg)
        else:
            overall = 0.0

        if capped_overall is not None:
            overall = min(overall, capped_overall)

        return GradeResponse(
            overall_band=overall,
            criteria=criteria_items,
            feedback=str(data.get("feedback", "")),
            suggestions=str(data.get("suggestions", "")),
            improved_version=data.get("improved_version"),
        )

    def grade_batch(self, task1_prompt: str, task1_essay: str, task2_prompt: str, task2_essay: str):
        """Chấm cả Task 1 và Task 2 trong một lần gọi."""
        res1 = self.grade_essay(task1_prompt, task1_essay, task_type="task1")
        res2 = self.grade_essay(task2_prompt, task2_essay, task_type="task2")
        return {"task1": res1, "task2": res2}


def _response_to_text(resp) -> str:
    """Trích text từ nhiều cấu trúc phản hồi google-genai một cách an toàn."""
    # Trường hợp đơn giản có thuộc tính text
    text = getattr(resp, "text", None)
    if isinstance(text, str) and text.strip():
        return text

    # Thử thuộc tính 'candidates' ~ resp.candidates[*].content.parts[*].text
    try:
        candidates = getattr(resp, "candidates", None) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            parts = getattr(content, "parts", None) or []
            for part in parts:
                t = getattr(part, "text", None)
                if isinstance(t, str) and t.strip():
                    return t
    except Exception:  # noqa: BLE001 - best effort extraction
        pass

    # Một số phiên bản có resp.output_text
    alt = getattr(resp, "output_text", None)
    if isinstance(alt, str) and alt.strip():
        return alt

    return ""


def _extract_json_dict(text: str) -> dict:
    """Cố gắng trích JSON từ văn bản tự do do LLM trả về."""
    import json
    import re

    if not text:
        return {}

    code_fence = re.search(r"```(?:json)?\n([\s\S]*?)\n```", text)
    candidate = code_fence.group(1) if code_fence else text

    start = candidate.find("{")
    end = candidate.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = candidate[start : end + 1]

    try:
        return json.loads(candidate)
    except Exception:
        return {}
