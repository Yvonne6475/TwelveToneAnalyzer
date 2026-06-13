from music21 import pitch

def transpose_row(row, interval):
    """将音列整体转位interval个半音"""
    return [(pc + interval) % 12 for pc in row]

def invert_row(row):
    """按第一音为轴进行倒影"""
    first = row[0]
    return [(2 * first - pc) % 12 for pc in row]

def retrograde_row(row):
    """逆行音列"""
    return list(reversed(row))

def all_forms(original_row):
    """
    生成48个变换形式：
    P0~P11, I0~I11, R0~R11, RI0~RI11
    """
    forms = {}
    for t in range(12):
        # Prime
        p = transpose_row(original_row, t)
        forms[f'P{t}'] = p

        # Inversion
        i = invert_row(original_row)
        i = transpose_row(i, t)
        forms[f'I{t}'] = i

        # Retrograde
        r = retrograde_row(original_row)
        r = transpose_row(r, t)
        forms[f'R{t}'] = r

        # Retrograde Inversion
        ri = invert_row(original_row)
        ri = retrograde_row(ri)
        ri = transpose_row(ri, t)
        forms[f'RI{t}'] = ri

    return forms

def identify_row_flexible(original_row, target_row, max_diff=3):
    """
    尝试识别 target_row 是否为 original_row 的某种标准12音变换形式。
    若不是，则返回最接近的形式（允许最多 max_diff 个音不同）
    """
    forms = all_forms(original_row)
    priority = ['P', 'I', 'R', 'RI']
    closest_name = None
    closest_form = None
    min_diff = max_diff + 1

    for prefix in priority:
        for t in range(12):
            name = f"{prefix}{t}"
            form = forms[name]
            # 比较差异数量
            diff_count = sum(1 for a, b in zip(form, target_row) if a != b)
            if diff_count == 0:
                return f"✅ 目标序列是原始序列的 {name} 形式"
            if diff_count < min_diff:
                min_diff = diff_count
                closest_name = name
                closest_form = form

    if min_diff <= max_diff:
        diff_indices = [i for i, (a, b) in enumerate(zip(closest_form, target_row)) if a != b]
        return (f"⚠️ 目标序列不是标准变换，但与 {closest_name} 最接近（相差 {min_diff} 个音）：\n"
                f"  - 标准: {closest_form}\n"
                f"  - 目标:  {target_row}\n"
                f"  - 不同位置: {diff_indices}")
    else:
        return "❌ 目标序列与任何标准变换都差距过大"

# ========== 示例测试 ==========

# 原始序列
original = [6, 9, 11, 4, 0, 2, 5, 7, 3, 8, 10, 1]

# 测试目标序列
# 正确 P4 = 全部音 +4
# 可试不同例子，如故意改错一个音进行模糊匹配测试
target = [4, 3, 11, 6, 9, 8, 5, 2, 11, 1, 4, 6]  # 最后音改错

# 匹配
result = identify_row_flexible(original, target, max_diff=4)
print(result)
