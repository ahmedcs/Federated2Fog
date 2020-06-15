import numpy as np
import random
from sklearn.model_selection import train_test_split
import syft as sy


def get_cluster_sizes(total, num_parts, uniform=True):
    parts = []
    if uniform:
        part_size = total//num_parts
        parts = [part_size] * num_parts
        for _ in range(total - sum(parts)):
            parts[2*_] += 1
    else:
        crossover = [0] + \
                    list(sorted(random.sample(range(2, total), num_parts-1))) \
                    + [total]
        for i in range(1, len(crossover)):
            parts.append(crossover[i]-crossover[i-1])

    return parts


def get_distributed_data(X_train, y_train, num_parts,
                         stratify=True, repeat=False, uniform=True):
    X_trains = []
    y_trains = []

    for i in range(num_parts-1):
        X_train, X_iter, y_train, y_iter = train_test_split(
            X_train, y_train, stratify=y_train, test_size=1/(num_parts-i))
        X_trains.append(X_iter)
        y_trains.append(y_iter)

    X_trains.append(X_train)
    y_trains.append(y_train)

    assert len(X_trains) == num_parts

    return X_trains, y_trains


def get_fog_graph(hook, num_workers, num_clusters,
                  shuffle_workers=True, uniform_clusters=True):
    # Define workers and layers
    workers = {}
    layer = 0
    for id_ in range(num_workers):
        name = 'L{}_W{}'.format(layer, id_)
        workers[name] = sy.VirtualWorker(hook, id=name)

    layer = 1
    for num_cluster in num_clusters:
        for id_ in range(num_cluster):
            name = 'L{}_W{}'.format(layer, id_)
            workers[name] = sy.VirtualWorker(hook, id=name)
        layer += 1

    agg_map = {}
    for l in range(1, len(num_clusters)+1):
        clustr_ids = [_ for _ in workers.keys() if 'L{}'.format(l) in _]
        worker_ids = [_ for _ in workers.keys() if 'L{}'.format(l-1) in _]
        if shuffle_workers:
            worker_ids = list(np.array(worker_ids)[
                np.random.permutation(len(worker_ids))])
        cluster_sizes = get_cluster_sizes(len(worker_ids),
                                          len(clustr_ids), uniform_clusters)
        indices = [sum(cluster_sizes[:id_])
                   for id_ in range(len(cluster_sizes)+1)]
        for id_ in range(len(clustr_ids)):
            agg_map[clustr_ids[id_]] = worker_ids[indices[id_]: indices[id_+1]]

    return agg_map, workers