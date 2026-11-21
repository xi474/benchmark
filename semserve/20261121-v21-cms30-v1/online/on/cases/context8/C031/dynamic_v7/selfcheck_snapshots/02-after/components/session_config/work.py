def compute(payload):
    """输出 rc（固定主提示 PROMPT>、续行提示 CONT>、禁用历史、追加 startup）、timeout（缺省 4）、markers（原顺序的 until，可为 null）。"""
    startup = payload.get("startup", "")
    if startup is None:
        startup = ""
    rc = "PS1='PROMPT> '\nPS2='CONT> '\nHISTFILE=/dev/null\n" + startup + "\n"
    timeout = payload.get("timeout_seconds", 4)
    if timeout is None:
        timeout = 4
    steps = payload.get("steps", [])
    markers = [step.get("until") for step in steps]
    return {"rc": rc, "timeout": timeout, "markers": markers}
