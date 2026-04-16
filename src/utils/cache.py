class QueryCache:
    """简单的内存缓存"""
    def __init__(self):
        self._cache = {}
    
    def get(self, key: str):
        return self._cache.get(key)
    
    def set(self, key: str, value):
        self._cache[key] = value