#!/usr/bin/env python3
"""
Redis Cache module
"""
import redis
import uuid
from typing import Union, Callable, Any
from functools import wraps


def track_call_count(method: Callable) -> Callable:
    """
    Tracks the number of calls made to a method in a Cache class.
    """
    @wraps(method)
    def invoker(self, *args, **kwargs) -> Any:
        """
        Invokes the given method after incrementing its call counter.
        """
        if isinstance(self._redis, redis.Redis):
            self._redis.incr(method.__qualname__)
        return method(self, *args, **kwargs)
    return invoker


def track_call_history(method: Callable) -> Callable:
    """
    Tracks the call details of a method in a Cache class.
    """
    @wraps(method)
    def invoker(self, *args, **kwargs) -> Any:
        """
        Returns the method's output after storing its inputs and output.
        """
        in_key = '{}:inputs'.format(method.__qualname__)
        out_key = '{}:outputs'.format(method.__qualname__)
        if isinstance(self._redis, redis.Redis):
            self._redis.rpush(in_key, str(args))
        result = method(self, *args, **kwargs)
        if isinstance(self._redis, redis.Redis):
            self._redis.rpush(out_key, result)
        return result
    return invoker


def display_call_history(method: Callable) -> None:
    """
    Displays the call history of a Cache class' method.
    """
    if method is None or not hasattr(method, '__self__'):
        return
    redis_inst = getattr(method.__self__, '_redis', None)
    if not isinstance(redis_inst, redis.Redis):
        return
    m_name = method.__qualname__
    in_key = '{}:inputs'.format(m_name)
    out_key = '{}:outputs'.format(m_name)
    call_count = 0
    if redis_inst.exists(m_name) != 0:
        call_count = int(redis_inst.get(m_name))
    print(f'{m_name} was called {call_count} times:')
    m_inputs = redis_inst.lrange(in_key, 0, -1)
    m_outputs = redis_inst.lrange(out_key, 0, -1)
    for m_input, m_output in zip(m_inputs, m_outputs):
        print(f'{m_name}(*{m_input.decode("utf-8")}) -> {m_output}')


class Cache:
    """
    Redis Cache class
    """
    def __init__(self):
        """
        Initializes a Redis client instance
        and flushes the database
        """
        self._redis = redis.Redis()
        self._redis.flushdb()

    @track_call_history
    @track_call_count
    def store(self, data: Union[str, bytes, int, float]) -> str:
        """
        Generates a random key, stores the input data in Redis
        using the random key, and returns the key.
        """
        key = str(uuid.uuid4())
        self._redis.set(key, data)
        return key

    def get(self, key: str, transform: Callable = None) -> Any:
        """
        Retrieves a value from a Redis data storage.
        """
        data = self._redis.get(key)
        return transform(data) if transform and data is not None else data

    def get_str(self, key: str) -> str:
        """
        Retrieves a string value from a Redis data storage.
        """
        return self.get(key, lambda x: x.decode('utf-8'))

    def get_int(self, key: str) -> int:
        """
        Retrieves an integer value from a Redis data storage.
        """
        return self.get(key, lambda x: int(x))
