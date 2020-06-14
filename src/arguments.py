from math import ceil

class Arguments():
    def __init__(self):
        self.num_train = 60000
        self.num_test = 10000
        self.num_workers = 50
        self.num_clusters = [5, 2, 1]
        self.uniform_clusters = True
        self.shuffle_workers = True
        self.batch_size = ceil(self.num_train/self.num_workers)
        self.test_batch_size = self.num_test
        self.epochs = 10
        self.lr = 0.01
        self.momentum = 0.5
        self.no_cuda = False
        self.seed = 1
        self.log_interval = 10
        self.save_model = True
        self.save_init = False
        self.load_init = True

