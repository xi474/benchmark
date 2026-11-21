def compute(payload):
    """按实际 stage 保留每个微批激活并反传；返回整题格式的 loss 和各层 gradients，采用微批等权和 float64。"""
    raise NotImplementedError
