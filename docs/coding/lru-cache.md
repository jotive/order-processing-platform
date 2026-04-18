# LRU Cache — O(1) `get` / `put`

LeetCode 146 · NeetCode Medium · 2026-04-18

## Problem

Design a cache with fixed capacity that evicts the **least recently used** entry when full. Both `get(key)` and `put(key, value)` must run in **O(1)** average time.

## Approach

The constraint that forces the design is "O(1) on both operations." A plain `dict` gives O(1) lookup but no order. A plain list gives order but O(n) on move-to-front. Neither alone is enough.

The standard solution combines both structures:

- A **hash map** `key → node` gives O(1) lookup.
- A **doubly linked list** of nodes gives O(1) insert, remove, and move-to-head — because we have direct pointers to every node through the map, we never traverse the list.

The head of the list is the most recently used entry; the tail is the eviction candidate.

- `get(key)` — hit: unlink the node, push to head, return value. Miss: return `-1`.
- `put(key, value)` — if the key exists, update and move to head. Otherwise insert a new head node; if size exceeds capacity, evict the tail and remove it from the map.

Sentinel head/tail nodes remove the boundary conditions in pointer updates — every real node always has a valid `prev` and `next`.

## Complexity

- **Time:** `O(1)` amortized for both `get` and `put`. Every operation is a constant number of hash lookups and pointer swaps; no traversal.
- **Space:** `O(capacity)` — one map entry and one list node per stored key.

## Why this maps to the Order Processing Platform

The same structural idea backs Redis — an in-memory key-value store with a bounded working set and an eviction policy. In this project, Redis caches hot reads (order lookups by ID) and stores idempotency keys with a TTL. The API code treats Redis as a black box, but understanding *why* `O(1)` access under eviction needs a hashmap plus an ordered structure is the same mental model that lets you reason about `maxmemory-policy allkeys-lru` when a production cache starts thrashing.

## Implementation

```python
class _Node:
    __slots__ = ("key", "value", "prev", "next")

    def __init__(self, key: int = 0, value: int = 0) -> None:
        self.key = key
        self.value = value
        self.prev: _Node | None = None
        self.next: _Node | None = None


class LRUCache:
    def __init__(self, capacity: int) -> None:
        self.capacity = capacity
        self.map: dict[int, _Node] = {}
        self.head = _Node()
        self.tail = _Node()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node: _Node) -> None:
        node.prev.next = node.next
        node.next.prev = node.prev

    def _push_front(self, node: _Node) -> None:
        node.prev = self.head
        node.next = self.head.next
        self.head.next.prev = node
        self.head.next = node

    def get(self, key: int) -> int:
        node = self.map.get(key)
        if node is None:
            return -1
        self._remove(node)
        self._push_front(node)
        return node.value

    def put(self, key: int, value: int) -> None:
        existing = self.map.get(key)
        if existing is not None:
            existing.value = value
            self._remove(existing)
            self._push_front(existing)
            return

        node = _Node(key, value)
        self.map[key] = node
        self._push_front(node)

        if len(self.map) > self.capacity:
            lru = self.tail.prev
            self._remove(lru)
            del self.map[lru.key]
```

## Tests

```python
def test_lru_cache_basic():
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1
    cache.put(3, 3)          # evicts key 2
    assert cache.get(2) == -1
    cache.put(4, 4)          # evicts key 1
    assert cache.get(1) == -1
    assert cache.get(3) == 3
    assert cache.get(4) == 4


def test_lru_cache_update_refreshes_recency():
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    cache.put(1, 10)         # 1 becomes most recent
    cache.put(3, 3)          # evicts 2, not 1
    assert cache.get(2) == -1
    assert cache.get(1) == 10
```
