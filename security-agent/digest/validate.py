"""The primary-source rule, enforced in code so nothing upstream can bend it."""
from urllib.parse import urlparse

from digest.sources import Item


def pre_cluster(items: list[Item]) -> list[list[Item]]:
    """Group items that share any CVE id (transitively); the rest stand alone."""
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    first_with: dict[str, int] = {}
    for i, item in enumerate(items):
        for cve in item.cve_ids:
            if cve in first_with:
                parent[find(i)] = find(first_with[cve])
            else:
                first_with[cve] = i
    groups: dict[int, list[Item]] = {}
    for i, item in enumerate(items):
        groups.setdefault(find(i), []).append(item)
    return list(groups.values())


def confirmable(cluster: list[Item]) -> bool:
    if any(i.kind == "primary" for i in cluster):
        return True
    hosts = {urlparse(i.url).hostname for i in cluster if i.kind == "outlet"}
    return len(hosts) >= 2
