import os
import re
import sys

# pip3 install pypinyin --break-system-packages
# python3 convert_to_ris.py
# 尝试导入 pypinyin，如果没有安装则提示用户
try:
    from pypinyin import pinyin, Style
except ImportError:
    print("【错误】缺少必要库 pypinyin")
    print("请先在终端运行安装命令: pip install pypinyin")
    sys.exit(1)

def format_name_case(name_part):
    """
    将名字部分格式化为首字母大写，其余小写
    例如: "JIA" -> "Jia", "ZHAO-YI" -> "Zhaoyi"
    """
    def replace_hyphen(match):
        return match.group(1).lower()
    
    # 处理连字符: -Y -> y
    name_part = re.sub(r'-([A-Za-z])', replace_hyphen, name_part)
    name_part = name_part.replace('-', '')
    
    return name_part.title()

def transliterate_chinese_name(chinese_name):
    """
    将中文姓名转换为拼音，格式：Last, First
    规则：第一个字为姓，后面的字为名
    例如：朱善良 -> Zhu, Shanliang
    """
    if not chinese_name:
        return ""
    
    # 按照用户规则：第一个字是姓
    surname_char = chinese_name[0]
    given_name_chars = chinese_name[1:]
    
    # 转换姓 (Style.NORMAL 获取不带声调的拼音)
    # pinyin 返回的是 [[py]] 列表结构
    surname_py_list = pinyin(surname_char, style=Style.NORMAL)
    if surname_py_list:
        surname = surname_py_list[0][0].title()
    else:
        surname = surname_char # 兜底
        
    # 转换名 (将剩余汉字拼音拼接)
    given_name_py_list = pinyin(given_name_chars, style=Style.NORMAL)
    # 将列表中的拼音取出并拼接，例如 [['shan'], ['liang']] -> 'shanliang'
    given_name_raw = "".join([x[0] for x in given_name_py_list])
    given_name = given_name_raw.title() # 首字母大写: Shanliang
    
    return f"{surname}, {given_name}"

def parse_author(author_str):
    """
    智能解析作者姓名
    1. 包含中文 -> 转拼音 (Last, First)
    2. 英文 -> 格式化为 (Last, First)
    """
    author_str = author_str.strip()
    if not author_str:
        return ""
        
    # 1. 检查是否包含中文
    if re.search(r'[\u4e00-\u9fa5]', author_str):
        # 仅处理纯中文名，如果夹杂英文可能需要特殊处理，这里假设是纯中文
        # 移除可能存在的空格
        clean_name = re.sub(r'\s+', '', author_str)
        return transliterate_chinese_name(clean_name)

    # 2. 英文处理逻辑 (保持之前的功能)
    if ',' in author_str:
        parts = author_str.split(',', 1)
        last_name = format_name_case(parts[0].strip())
        first_name = format_name_case(parts[1].strip())
        return f"{last_name}, {first_name}"
    
    parts = author_str.split()
    if len(parts) == 1:
        return format_name_case(parts[0])
    
    # 尝试识别全大写的姓 (如 Wentao JIA)
    last_name_index = -1
    for i, part in enumerate(parts):
        if part.isupper() and len(part) > 1:
            last_name_index = i
            break
            
    if last_name_index != -1:
        last_name = parts[last_name_index]
        first_names = parts[:last_name_index] + parts[last_name_index+1:]
        last = format_name_case(last_name)
        first = " ".join([format_name_case(n) for n in first_names])
        return f"{last}, {first}"
    else:
        # 默认最后一个词是姓
        last_name = parts[-1]
        first_names = parts[:-1]
        last = format_name_case(last_name)
        first = " ".join([format_name_case(n) for n in first_names])
        return f"{last}, {first}"

def clean_volume(vol_str):
    if not vol_str: return ""
    if ';' in vol_str: vol_str = vol_str.split(';')[0]
    return re.sub(r'(?:vol\.?|v\.?|no\.?)\s*', '', vol_str, flags=re.IGNORECASE).strip()

def map_type_to_ris(type_str):
    type_str = type_str.strip()
    if '期刊' in type_str or 'Journal' in type_str: return 'JOUR'
    elif '会议' in type_str or 'Conference' in type_str: return 'CPAPER'
    elif '学位' in type_str or 'Thesis' in type_str: return 'THES'
    elif '专利' in type_str or 'Patent' in type_str: return 'PAT'
    else: return 'JOUR'

def process_entry(entry_text):
    lines = entry_text.strip().splitlines()
    data = {}
    
    for line in lines:
        if '-' in line:
            parts = line.split('-', 1)
            if len(parts) == 2:
                key = parts[0].strip()
                value = parts[1].strip()
                match = re.match(r'^[^a-zA-Z0-9]+\s+(.*)', value)
                if match: value = match.group(1)
                if value: data[key] = value

    if 'Title' not in data and '题名' not in str(data): return None

    ris_lines = []
    
    # 类型
    ris_type = map_type_to_ris(data.get('Type', 'Journal'))
    ris_lines.append(f"TY  - {ris_type}")
    
    # 作者处理
    if 'Author' in data:
        # 分割作者 (支持中文分号、英文分号、中文逗号)
        authors = re.split(r'[;；]', data['Author'])
        for au in authors:
            au = au.strip()
            if au:
                formatted_au = parse_author(au)
                ris_lines.append(f"AU  - {formatted_au}")
    
    # 标题 (T1)
    if 'Title' in data: ris_lines.append(f"T1  - {data['Title']}")
    
    # 刊名
    if 'Source' in data:
        tag = 'T2' if ris_type == 'CPAPER' else 'JF'
        ris_lines.append(f"{tag}  - {data['Source']}")
            
    # 日期
    if 'Time' in data:
        ris_lines.append(f"PY  - {data['Time'].replace('-', '/')}")
    elif 'Year' in data:
        ris_lines.append(f"PY  - {data['Year']}///")
        
    # 卷/期/页
    if 'Roll' in data:
        vl = clean_volume(data['Roll'])
        if vl: ris_lines.append(f"VL  - {vl}")
    if 'Period' in data: ris_lines.append(f"IS  - {data['Period']}")
    if 'PageCount' in data:
        pages = data['PageCount'].split('-')
        if len(pages) >= 1: ris_lines.append(f"SP  - {pages[0].strip()}")
        if len(pages) >= 2: ris_lines.append(f"EP  - {pages[1].strip()}")
            
    # 其他
    if 'DOI' in data: ris_lines.append(f"DO  - {data['DOI']}")
    if 'ISSN' in data: ris_lines.append(f"SN  - {data['ISSN']}")
    if 'Summary' in data: ris_lines.append(f"AB  - {data['Summary']}")
    if 'Keyword' in data:
        kws = re.split(r'[;；]', data['Keyword'].replace(';;', ';'))
        for kw in kws:
            if kw.strip(): ris_lines.append(f"KW  - {kw.strip()}")
                
    ris_lines.append("ER  - ")
    ris_lines.append("")
    return "\n".join(ris_lines)

def read_file_smart(file_path):
    encodings = ['gb18030', 'utf-8', 'utf-8-sig', 'gbk', 'utf-16']
    for enc in encodings:
        try:
            with open(file_path, 'r', encoding=enc) as f:
                content = f.read()
                if 'Type-' in content: return content, enc
        except UnicodeDecodeError: continue
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        return f.read(), 'utf-8-forced'

def convert_files_with_pinyin(input_dir):
    files = [f for f in os.listdir(input_dir) if f.endswith(".txt")]
    if not files:
        print(f"目录 '{input_dir}' 下没有 .txt 文件。")
        return
    print(f"找到 {len(files)} 个文件，开始处理...\n")

    for filename in files:
        file_path = os.path.join(input_dir, filename)
        output_filename = os.path.splitext(filename)[0] + ".ris"
        output_path = os.path.join(input_dir, output_filename)
        
        try:
            content, enc = read_file_smart(file_path)
            content = content.replace('\r\n', '\n').replace('\r', '\n')
            
            # 分割条目
            raw_entries = re.split(r'(?=Type-)', content)
            
            valid_entries = []
            for entry in raw_entries:
                if not entry.strip(): continue
                if 'Title-' not in entry and '题名' not in entry: continue
                
                ris_str = process_entry(entry)
                if ris_str: valid_entries.append(ris_str)
            
            if valid_entries:
                with open(output_path, 'w', encoding='utf-8') as f_out:
                    f_out.write("\n".join(valid_entries))
                print(f"[成功] {filename} -> {output_filename} (编码: {enc}, 提取: {len(valid_entries)})")
            else:
                print(f"[失败] {filename} 未找到有效条目。")
                
        except Exception as e:
            print(f"[错误] 处理 {filename} 时出错: {str(e)}")
    print("\n处理结束。")

if __name__ == "__main__":
    convert_files_with_pinyin('.')