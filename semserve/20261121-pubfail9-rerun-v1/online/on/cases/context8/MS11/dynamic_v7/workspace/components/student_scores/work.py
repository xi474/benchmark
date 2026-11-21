def compute(payload):
    """按学生 ID 输出课程 1、2 非空成绩的百分制整型均值（sum×100 整除数量）。"""
    sums = {}
    counts = {}
    for student, course, score in payload["grades"]:
        if course not in (1, 2):
            continue
        if score is None:
            continue
        sums[student] = sums.get(student, 0) + score
        counts[student] = counts.get(student, 0) + 1
    return {s: sums[s] * 100 // counts[s] for s in sums}
