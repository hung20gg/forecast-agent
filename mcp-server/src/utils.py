import re

def normalize_search_query(query: str) -> str:
    """Escape BigQuery SEARCH reserved characters with a backslash."""
    # Reserved characters: \ + - & | ! ( ) { } [ ] ^ " ~ * ? : / '
    reserved = "\\+-&|!(){}[]^\"~*?:/'"
    result = []
    for ch in query:
        if ch in reserved:
            result.append('\\' + ch)
        else:
            result.append(ch)
    return ''.join(result)