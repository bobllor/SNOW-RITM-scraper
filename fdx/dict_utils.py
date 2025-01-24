def get_key_value(data: dict, target: str,) -> str | None:
    '''Searches and returns the value of a key in a `dict` at any nesting level, else None if not found.
    '''
    if not isinstance(data, dict):
        return None
    
    extracted_target = data.get(target)

    if extracted_target is not None:
        return extracted_target
    
    for value in data.values():
        result = None

        if isinstance(value, dict):
            result = get_key_value(value, target)
        elif isinstance(value, list):
            for ele in value:
                result = get_key_value(ele, target)

        if result is not None:
            return result
    
    return None

def set_key_value(data: dict, target: str, value: any, *, blacklist: set[str] = set()) -> int:
    '''Searches and changes the value of a target key in a `dict` at any nesting level.

    Returns `1` if the `dict` was successfully modified, else `0`.

    Required Parameters
    --------
        `data`: A `dict` containing a key that is being modified.

        `target`: A `str` that is the target key to modify.

        `value`: The value that is overwriting the `data[key]` value. This can be any valid JSON variable.

    Optional Parameters
    --------
        `blacklist`: `set` containing `str` elements which the function will skip if it is in the `set`. 
        Required if the `dict` contains multiple keys of the same name at different nesting levels, else default is an empty `set`.
    '''    
    for key in data:
        var = data[key]
        result = 0

        if key == target:
            data[key] = value
            return 1

        if key in blacklist:
            continue
        
        if isinstance(var, dict):
            result = set_key_value(var, target, value, blacklist=blacklist)
        elif isinstance(var, list):
            for ele in var:
                result = set_key_value(ele, target, value, blacklist=blacklist)
            
        if result:
            return 1
    
    return 0