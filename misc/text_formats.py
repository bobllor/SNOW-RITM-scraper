def element_text_format(element_list: list, task_type: str) -> str:
    text = task_type

    if len(element_list) > 1:
        text = task_type + 's'
    
    if len(element_list) == 0:
        text = f'no {task_type}s' 
    
    return text