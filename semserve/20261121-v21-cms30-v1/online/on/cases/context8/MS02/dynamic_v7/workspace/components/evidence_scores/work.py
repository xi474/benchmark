def compute(payload):
    """按主题输入顺序生成评分表；每行把具有效章节证据的论文 ID 映射到该主题最高质量分。"""
    topics = payload["topics"]
    papers = payload["papers"]
    result = []
    for topic in topics:
        row = {}
        for paper in papers:
            methods = set(paper["methods"])
            best = None
            for claim in paper["claims"]:
                c_topic, c_section, c_quality = claim
                if c_topic == topic and c_section in methods:
                    if best is None or c_quality > best:
                        best = c_quality
            if best is not None:
                row[paper["id"]] = best
        result.append(row)
    return result
