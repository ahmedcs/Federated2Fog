from arguments import Arguments
from svm import SVM
from distributor import get_fog_graph
from train import fog_train as train, test
import os
import pickle as pkl
import syft as sy
import sys
import torch
from torchvision import datasets, transforms


# Setups
args = Arguments()
hook = sy.TorchHook(torch)
USE_CUDA = not args.no_cuda and torch.cuda.is_available()

torch.manual_seed(args.seed)
device = torch.device("cuda" if USE_CUDA else "cpu")
kwargs = {'num_workers': 1, 'pin_memory': True} if USE_CUDA else {}
kwargs = {}

for non_iid in range(1, 2):
    non_iid = args.non_iid
    ckpt_path = '../ckpts'
    dataset = 'mnist'
    clf_type = 'svm'
    paradigm = 'fog_uniform_non_iid_{}_num_workers_{}_lr_{}_batch_{}_laplace_rounds_{}_radius_{}_d2d_{}_factor_{}_alpha_{}'
    if args.dynamic_alpha:
        paradigm += '_dyn_{}_delta_{}_omega_{}'

    paradigm = paradigm.format(
        non_iid, args.num_workers, args.lr, args.batch_size,
        args.rounds, args.radius, args.d2d, args.factor,
        args.alpha, args.dynamic_alpha, args.delta, args.omega
    )
    model_name = '{}_{}_{}'.format(dataset, clf_type, paradigm)
    file_ = '../logs/{}.log'.format(model_name)
    print("Logging: ", file_)
    log_file = open(file_, 'w')
    std_out = sys.stdout
    sys.stdout = log_file
    print('+'*80)
    print(model_name)
    print('+'*80)
    
    init_path = '../init/mnist_svm.init'
    best_path = os.path.join(ckpt_path, model_name + '.best')
    stop_path = os.path.join(ckpt_path, model_name + '.stop')

    # prepare graph and data
    fog_graph, workers = get_fog_graph(hook, args.num_workers,
                                       args.num_clusters,
                                       args.shuffle_workers,
                                       args.uniform_clusters)

    test_loader = torch.utils.data.DataLoader(
        datasets.MNIST('../data', train=False, transform=transforms.Compose([
                           transforms.ToTensor(),
                           transforms.Normalize((0.1307,), (0.3081,))
                       ])),
        batch_size=args.test_batch_size, shuffle=True, **kwargs)

    if non_iid == 10:
        data_file = '../ckpts/data_iid_num_workers_{}_stratify_True_uniform_True.pkl'.format(args.num_workers)
    else:
        data_file = '../ckpts/data_non_iid_{}_num_workers_{}_stratify_True_uniform_True.pkl'.format(
            non_iid, args.num_workers)
    print('Loading data: {}'.format(data_file))
    X_trains, y_trains = pkl.load(
        open(data_file, 'rb'))

    print(fog_graph)

    best = 0

    # Fire the engines
    model = SVM().to(device)
    num_params = model.state_dict
    model.load_state_dict(torch.load(init_path))
    print('Load init: {}'.format(init_path))

    best = 0

    x_ax = []
    y_ax = []
    l_test = []
    grad_tr = []
    rounds_tr = []
    div_tr = []
    alpha_store = {}
    grad = {'weight': 0}
    for epoch in range(1, args.epochs + 1):
        grad, rounds, div, alpha_store = train(
            args, model, fog_graph, workers, X_trains, y_trains, device, epoch,
            'hinge', 'laplacian', args.rounds, args.radius, args.d2d,
            args.factor, alpha_store=alpha_store, prev_grad=grad['weight'])
        acc, loss = test(args, model, device, test_loader, best, epoch, 'hinge')
        y_ax.append(acc)
        x_ax.append(epoch)
        l_test.append(loss)
        grad_tr.append(grad)
        rounds_tr.append(rounds)
        div_tr.append(div)

        if args.save_model and acc > best:
            best = acc
            torch.save(model.state_dict(), best_path)
            print('Model best  @ {}, acc {}: {}\n'.format(
                epoch, acc, best_path))

    if (args.save_model):
        torch.save(model.state_dict(), stop_path)
        print('Model stop: {}'.format(stop_path))

    hist_file = '../history/history_{}.pkl'.format(model_name)
    pkl.dump((x_ax, y_ax, l_test, grad_tr, rounds_tr, div_tr), open(hist_file, 'wb'))
    print('Saved: ', hist_file)

    import matplotlib.pyplot as plt
    plt.plot(x_ax, y_ax)
    plot_file = '../plots/{}.png'.format(model_name)
    plt.savefig(plot_file)
    print('Saved: ', plot_file)

    log_file.close()
    sys.stdout = std_out