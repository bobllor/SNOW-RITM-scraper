def access_key(data: dict, target: str) -> str | None:
    '''Searches and returns the `value` of a key in a `dict` at any nesting level, else None if not found.
    '''
    if not isinstance(data, dict):
        return None
    
    extracted_target = data.get(target)

    if extracted_target is not None:
        return extracted_target
    
    for value in data.values():
        result = None

        if isinstance(value, dict):
            result = access_key(value, target)
        elif isinstance(value, list):
            for ele in value:
                result = access_key(ele, target)
        else:
            continue

        if result is not None:
            return result
    
    return None