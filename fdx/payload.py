import json

def set_metadata():
    '''Sets the metadata of the label for any modifications.'''
    
def get_metadata() -> dict:
    '''Returns a `dict` of the default json values for the payload.'''
    with open('./fdx/label_metadata.json', 'r') as file:
        json_data = json.load(file)
    
    return json_data

def get_payload():
    with open('./fdx/data.json', 'r') as file:
        json_data = json.load(file)
    
    return json_data