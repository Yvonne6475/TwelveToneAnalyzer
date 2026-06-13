import numpy as np
from itertools import combinations
from music21 import chord

# 你的原始音集
arr5_35 = np.array([0, 2, 4, 7, 9])

# 生成子集
arr_tetrachords = list(combinations(arr5_35, 4))  # 四音
arr_tritones = list(combinations(arr5_35, 3))     # 三音

# ===================== 开头打印：原始四音子集 =====================
print("===== 原始四音子集 =====")
for s in arr_tetrachords:
    print([int(x) for x in s])

# ===================== 开头打印：原始三音子集 =====================
print("\n===== 原始三音子集 =====")
for s in arr_tritones:
    print([int(x) for x in s])

# 合并成一个列表（不用vstack，避免维度错误）
all_subsets = arr_tetrachords + arr_tritones

# 转普通int（修复music21报错）
def to_int(pcs):
    return [int(x) for x in pcs]

# ===================== 第一步：批量算出所有 forte =====================
all_forte = []
all_pcs = []

for s in all_subsets:
    pcs = to_int(s)
    c = chord.Chord(pcs)
    all_pcs.append(pcs)
    all_forte.append(c.forteClass)

# 转 numpy 数组
forte_np = np.array(all_forte)
pcs_np = np.array(all_pcs, dtype=object)

# ===================== 第二步：np.unique 去重（核心）=====================
unique_forte, idx = np.unique(forte_np, return_index=True)

# 去重后的最终集合
final_pcs = pcs_np[idx]

# ===================== 第三步：输出 =====================
print("\n============ 去重后（按 Forte 类）============\n")
for pcs in final_pcs:
    c = chord.Chord(list(pcs))
    print(f"{pcs} -> normalOrder: {c.normalOrder} | Prime: {c.primeForm} | Forte: {c.forteClass}")