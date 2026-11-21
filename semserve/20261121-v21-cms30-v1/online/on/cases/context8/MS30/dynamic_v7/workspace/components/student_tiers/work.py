def compute(payload):
    """使用 16、17 号课程非空成绩的精确分数比，按原门槛输出学生到 P/D/N 层级映射。"""
    grades = payload["grades"]
    ratios = {}
    for student, course, score, full in grades:
        if course not in (16, 17):
            continue
        if score is None or full is None:
            continue
        ratios.setdefault(student, []).append(score / full)
    result = {}
    for student, rs in ratios.items():
        avg = sum(rs) / len(rs)
        if avg < 0.60:
            tier = "N"
        elif avg < 0.75:
            tier = "D"
        else:
            tier = "P"
        result[student] = tier
    return result
