import datetime
import torch
import numpy as np
import yaml
import glob
import os
import shutil
import math
import random
import time
import torch.nn as nn
import torch.nn.functional as F
import torch_optimizer as optim
from torch.utils.data import Dataset
from torch.utils.data.sampler import SubsetRandomSampler
from ignite.engine import Engine, Events
from ignite.metrics import Loss, Metric
from ignite.utils import convert_tensor
import tensorboardX
from random import choices, sample, seed, shuffle

# --- was: `from network import TabEstimator, CustomLoss` ---
# network.py has been split into two files:
#   tab_estimator_model.py -> TabEstimator, CustomLoss, GuidedAttentionLoss, ConvStack
#   encoder_modules.py     -> ASRInterface, ConformerEncoder,
#                              subsequent_mask, make_non_pad_mask, make_pad_mask, mask_by_length
# tab_estimator_model.py already imports the encoder pieces it needs from
# encoder_modules.py internally, so train.py only needs the model + loss.
from tab_estimator_model import TabEstimator, CustomLoss, InhibitionLoss


def _load_pairwise_matrix(path, key=None):
    """Load a pairwise likelihood/inhibition weight matrix from either a
    plain .npy file or an .npz archive (as produced by, e.g., a custom
    training pipeline for `estimate_pairwise_likelihood.py`-style output).

    Args:
        path: path to a .npy or .npz file.
        key: for .npz files with multiple arrays, the array name to use.
            If None and the archive contains exactly one array, that array
            is used automatically; otherwise a ValueError is raised
            listing the available keys so the correct one can be chosen.
    """
    if path.endswith(".npz"):
        with np.load(path) as npz:
            keys = list(npz.keys())
            if key is not None:
                if key not in keys:
                    raise KeyError(
                        f"key {key!r} not found in {path!r}; available keys: {keys}")
                return npz[key]
            if len(keys) == 1:
                return npz[keys[0]]
            raise ValueError(
                f"{path!r} contains multiple arrays {keys}; set "
                f"pairwise_likelihood_key in config.yaml to pick one")
    return np.load(path)




class LossWrapper(Loss):
    def __init__(self, loss_fn, output_transform=lambda x: x,
                 batch_size=lambda x: len(x)):
        super(LossWrapper, self).__init__(
            loss_fn, output_transform=output_transform, batch_size=batch_size)

    def update(self, output):

        (frame_pred, frame_gt, note_pred, note_gt, attn_map, olens, note_len,note_onset_pred, note_onset_gt) = output
        loss = self._loss_fn(frame_pred, frame_gt.float(), note_pred, note_gt.float(),
                                  attn_map, olens, note_len,
                                  note_onset_pred=note_onset_pred, note_onset_gt=note_onset_gt.float())

        average_loss = loss
        if len(average_loss.shape) != 0:
            raise ValueError("loss_fn did not return an average loss.")

        N = self._batch_size(frame_gt)
        self._sum += average_loss.item() * N
        self._num_examples += N


class CustomDataset(Dataset):
    def __init__(self, data_list, mode, input_feature_type):
        self.data_list = data_list
        self.mode = mode
        self.input_feature_type = input_feature_type

    def __len__(self):
        return len(self.data_list)

    def __getitem__(self, index):
        data = np.load(self.data_list[index])
        input_features = data["cqt"]

        note_gt = data["tab"]
        frame_gt = data["frame_tab"]
        note_onset_gt = data["tab_onset"]

        bpm = data["tempo"]

        frame_len = input_features.shape[0]
        note_len = note_gt.shape[0]

        return input_features, frame_gt, note_gt, note_onset_gt, frame_len, note_len, bpm


def _prepare_batch(batch, mode, device=None, non_blocking=False):
    """
    Prepare batch for training: pass to a device with options.
    """
    input_features, frame_gt, note_gt, note_onset_gt, frame_len, note_len, bpm = batch

    return (convert_tensor(input_features, device=device, non_blocking=non_blocking),
            convert_tensor(frame_gt, device=device, non_blocking=non_blocking),
            convert_tensor(note_gt, device=device, non_blocking=non_blocking),
            convert_tensor(note_onset_gt, device=device, non_blocking=non_blocking),
            convert_tensor(frame_len, device=device,
                           non_blocking=non_blocking),
            convert_tensor(note_len, device=device, non_blocking=non_blocking),
            convert_tensor(bpm, device=device, non_blocking=non_blocking))


def tab_pad_collate(batch):
    input_features, frame_tab, note_tab, note_onset, frame_len, note_len, bpm = zip(*batch)
    batch_size = len(input_features)

    frame_maxlen, note_maxlen = np.max(frame_len), np.max(note_len)

    frame_len = np.asarray(frame_len)
    note_len = np.asarray(note_len)
    bpm = np.asarray(bpm)
    for batch_n in range(batch_size):
        frame_padlen = frame_maxlen - frame_len[batch_n]
        note_padlen = note_maxlen - note_len[batch_n]
        padded_input_features = np.pad(
            input_features[batch_n], [(0, frame_padlen), (0, 0)], 'constant')
        padded_note_tab = np.pad(
            note_tab[batch_n], [(0, note_padlen), (0, 0), (0, 0)], 'constant')
        padded_frame_tab = np.pad(
            frame_tab[batch_n], [(0, frame_padlen), (0, 0), (0, 0)], 'constant')
        padded_note_onset = np.pad(
            note_onset[batch_n], [(0, note_padlen), (0, 0), (0, 0)], 'constant')

        if batch_n == 0:
            padded_input_features_out = np.expand_dims(
                padded_input_features, axis=0)
            padded_note_tab_out = np.expand_dims(padded_note_tab, axis=0)
            padded_frame_tab_out = np.expand_dims(padded_frame_tab, axis=0)
            padded_note_onset_out = np.expand_dims(padded_note_onset, axis=0)
        else:
            padded_input_features_out = np.append(
                padded_input_features_out, np.expand_dims(padded_input_features, axis=0), axis=0)
            padded_note_tab_out = np.append(
                padded_note_tab_out, np.expand_dims(padded_note_tab, axis=0), axis=0)
            padded_frame_tab_out = np.append(
                padded_frame_tab_out, np.expand_dims(padded_frame_tab, axis=0), axis=0)
            padded_note_onset_out = np.append(
                padded_note_onset_out, np.expand_dims(padded_note_onset, axis=0), axis=0)

    # reverse sort by length
    sort_idx = np.argsort(frame_len)[::-1]
    padded_input_features_out = np.take(
        padded_input_features_out, sort_idx, axis=0)
    padded_note_tab_out = np.take(padded_note_tab_out, sort_idx, axis=0)
    padded_frame_tab_out = np.take(padded_frame_tab_out, sort_idx, axis=0)
    padded_note_onset_out = np.take(padded_note_onset_out, sort_idx, axis=0)
    frame_len = np.take(frame_len, sort_idx, axis=0)
    note_len = np.take(note_len, sort_idx, axis=0)
    bpm = np.take(bpm, sort_idx, axis=0)

    return torch.from_numpy(padded_input_features_out), torch.from_numpy(padded_frame_tab_out), torch.from_numpy(padded_note_tab_out), torch.from_numpy(padded_note_onset_out),  torch.from_numpy(frame_len), torch.from_numpy(note_len), torch.from_numpy(bpm)


def train(mode, input_feature_type, use_custom_decimation_func, use_conv_stack, use_galoss, test_num, train_data_list, valid_data_list, tensorboard_dir, model_dir, epoch, lr,  d_model, encoder_heads, encoder_layers, n_cores, device, n_bins, hop_length, sr,
          inhibition_lambda=0.0, pairwise_likelihood_path=None, inhibition_boost=1, pairwise_likelihood_key=None):
    """
    Uses the Conformer encoder and the Logistic output formulation
    (Sec. 2.2 of arXiv:2204.08094), which is required to enable the
    pairwise inhibition loss.
    inhibition_lambda: lambda in Eq. (9), L_total = L_BCE + lambda * L_inh.
        Set to 0 to train the Logistic formulation without inhibition
        (paper's Experiment 4).
    pairwise_likelihood_path: path to a .npy or .npz pairwise likelihood/
        inhibition weight matrix. Required when inhibition_lambda > 0; a
        ValueError is raised otherwise.
    inhibition_boost: boost exponent b in Eq. (7), applied on-the-fly if
        `pairwise_likelihood_path` points to a *raw* IoU matrix (i.e. was
        produced with --boost 1). Ignored if the loaded matrix already has
        boosting baked in, in which case leave this at 1.
    pairwise_likelihood_key: for .npz files containing more than one
        array, the array name holding the matrix. Not needed for .npy
        files, or for .npz files with a single array.
    """
    writer = tensorboardX.SummaryWriter(tensorboard_dir)
    torch.backends.cudnn.benchmark = True
    torch.backends.cudnn.deterministic = True

    model = TabEstimator(mode, use_custom_decimation_func, use_conv_stack, n_bins, hop_length, sr, encoder_heads=encoder_heads,
                         encoder_layers=encoder_layers)
    for p in model.parameters():
        if p.dim() > 1:
            nn.init.xavier_uniform_(p)

    inhibition_loss_module = None
    if inhibition_lambda > 0:
        if pairwise_likelihood_path is None:
            raise ValueError(
                "inhibition_lambda > 0 requires pairwise_likelihood_path to "
                "be set in config.yaml -- point it at your trained "
                "inhibition matrix (.npy or .npz).")

        iou_or_weights = _load_pairwise_matrix(
            pairwise_likelihood_path, key=pairwise_likelihood_key)
        if inhibition_boost != 1:
            # matrix on disk is treated as a raw IoU matrix; boost it
            # on-the-fly per Eq. (7)
            inhibition_loss_module = InhibitionLoss.from_pairwise_likelihood(
                iou_or_weights, boost=inhibition_boost)
        else:
            # matrix on disk is already the inhibition weight matrix
            # (or boost=1 is intentional, i.e. w = 1 - IoU)
            inhibition_loss_module = InhibitionLoss.from_pairwise_likelihood(
                iou_or_weights, boost=1)
        print(f"[inhibition] loaded pairwise likelihood matrix from "
              f"{pairwise_likelihood_path} (boost={inhibition_boost})")

    criterion = CustomLoss(mode, use_galoss, use_onset_loss=True,
                            inhibition_loss=inhibition_loss_module,
                            inhibition_lambda=inhibition_lambda)
    optimizer = optim.RAdam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(
        optimizer, 32, gamma=0.5)

    model.cuda()
    criterion.cuda()
    device = "cuda"

    train_dataset = CustomDataset(train_data_list, mode, input_feature_type)
    valid_dataset = CustomDataset(valid_data_list, mode, input_feature_type)
    train_loader = torch.utils.data.DataLoader(
        dataset=train_dataset,
        batch_size=32,
        shuffle=True,
        collate_fn=tab_pad_collate,
        num_workers=n_cores,
        pin_memory=False)
    valid_loader = torch.utils.data.DataLoader(
        dataset=valid_dataset,
        batch_size=1,
        shuffle=False,
        num_workers=n_cores,
        pin_memory=False)

    class Loss_container():
        def __init__(self):
            self.loss_value = 0
            self.epoch_loss_value = 0

        def _reset_itr(self):
            self.loss_value = 0

        def update_itr(self):
            self.epoch_loss_value += self.loss_value
            self._reset_itr()

        def reset_epoch(self):
            self.epoch_loss_value = 0

    loss_container = Loss_container()

    def _update(engine, batch):
        model.train()
        optimizer.zero_grad()
        padded_input_features, padded_frame_tab_gt, note_tab_gt, note_onset_gt, frame_len, note_len, bpm = _prepare_batch(
            batch, mode, device=device)

        frame_pred, note_pred, note_onset_pred, olens = model(
            padded_input_features.float(), frame_len, note_len, bpm)
        encoder_self_attn_map = model.encoder.encoders._modules['0']._modules['self_attn'].attn
        loss = criterion(frame_pred, padded_frame_tab_gt, note_pred,
                         note_tab_gt, encoder_self_attn_map, olens, note_len, note_onset_pred=note_onset_pred, note_onset_gt=note_onset_gt.float())
        loss_container.loss_value += loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1)
        optimizer.step()
        return loss.item()

    def _inference(engine, batch):
        model.eval()
        with torch.no_grad():
            padded_input_features, padded_frame_tab_gt, note_tab_gt, note_onset_gt, frame_len, note_len, bpm = _prepare_batch(
                batch, mode, device=device)

            frame_pred, note_pred, note_onset_pred, olens = model(padded_input_features.float(), frame_len, note_len, bpm)
            encoder_self_attn_map = model.encoder.encoders._modules['0']._modules['self_attn'].attn
            return frame_pred, padded_frame_tab_gt, note_pred, note_tab_gt, encoder_self_attn_map, olens, note_len, note_onset_pred, note_onset_gt.float()

    trainer = Engine(_update)
    evaluator = Engine(_inference)
    metrics = {"Loss": LossWrapper(criterion)}
    for name, metric in metrics.items():
        metric.attach(evaluator, name)

    @trainer.on(Events.ITERATION_COMPLETED)
    def log_training_loss(trainer):
        writer.add_scalar("train/loss", trainer.state.output,
                          trainer.state.iteration)
        loss_container.update_itr()

    @trainer.on(Events.EPOCH_COMPLETED)
    def log_training_results(trainer):
        avg_loss = loss_container.epoch_loss_value / len(train_loader)
        print("Training Results \t- Epoch: {}  Avg loss: {:.4f}"
              .format(trainer.state.epoch, avg_loss))
        writer.add_scalar("train/avg_loss",
                          avg_loss, trainer.state.epoch)
        loss_container.reset_epoch()
        if trainer.state.epoch % 32 == 0:
            modelname = "epoch{}.model".format(trainer.state.epoch)
            if not os.path.exists(model_dir):
                os.makedirs(model_dir)
            torch.save(model.state_dict(), os.path.join(model_dir, modelname))
        scheduler.step()

    @trainer.on(Events.EPOCH_COMPLETED)
    def log_validation_results(trainer):
        evaluator.run(valid_loader)
        metrics = evaluator.state.metrics
        print("Validation Results \t- Epoch: {}  Avg loss: {:.4f}"
              .format(trainer.state.epoch, metrics["Loss"]))
        writer.add_scalar("valid/avg_loss",
                          metrics["Loss"], trainer.state.epoch)

    trainer.run(train_loader, max_epochs=epoch)
    writer.close()
    return


def main(mode, input_feature_type, use_custom_decimation_func, use_conv_stack, use_galoss, train_ratio, note_resolution, epoch, lr, seed_, d_model, encoder_heads, encoder_layers, n_cores, cqt_n_bins, hop_length, sr,
         inhibition_lambda=0.0, pairwise_likelihood_path=None, inhibition_boost=1, pairwise_likelihood_key=None):
    data_path = os.path.join(
        "data", "npz", f"original", "split", "*.npz")
    data_list = np.array(glob.glob(data_path, recursive=True))

    now = datetime.datetime.now()
    tensorboard_dir = os.path.join("tensorboard", "{0:%Y%m%d%H%M}".format(now))
    model_dir = os.path.join("model", "{0:%Y%m%d%H%M}".format(now))
    os.makedirs(model_dir)

    n_bins = cqt_n_bins

    shutil.copyfile("src/config.yaml", model_dir + "/config.yaml")

    if torch.cuda.is_available():
        device = 'cuda'
        for test_num in range(6):
            dev_data_list = [datapath for datapath in data_list if not(
                os.path.split(datapath)[1].startswith(f"0{test_num}_"))]
            random.shuffle(dev_data_list)
            train_data_list = dev_data_list[:int(
                round(len(dev_data_list) * train_ratio))]
            valid_data_list = dev_data_list[int(
                round(len(dev_data_list) * train_ratio)):]
            tensorboard_dir = os.path.join(
                "tensorboard", "{0:%Y%m%d%H%M}".format(now), f"testNo0{test_num}")
            model_dir = os.path.join(
                "model", "{0:%Y%m%d%H%M}".format(now), f"testNo0{test_num}")
            train(mode, input_feature_type, use_custom_decimation_func, use_conv_stack, use_galoss, test_num, train_data_list, valid_data_list, tensorboard_dir, model_dir,
                  epoch, lr, d_model, encoder_heads, encoder_layers, n_cores, device, n_bins, hop_length, sr,
                  inhibition_lambda=inhibition_lambda,
                  pairwise_likelihood_path=pairwise_likelihood_path, inhibition_boost=inhibition_boost,
                  pairwise_likelihood_key=pairwise_likelihood_key)
    else:
        raise EnvironmentError("CUDA is not avaible")

    return


if __name__ == "__main__":
    with open("src/config.yaml") as f:
        obj = yaml.safe_load(f)
        hop_length = obj["hop_length"]
        sr = obj["down_sampling_rate"]
        train_ratio = obj["train_ratio"]
        note_resolution = obj["note_resolution"]
        cqt_n_bins = obj["cqt_n_bins"]
        epoch = obj["epoch"]
        lr = obj["lr"]
        seed_ = obj["seed_"]
        d_model = obj["d_model"]
        encoder_heads = obj["encoder_heads"]
        encoder_layers = obj["encoder_layers"]
        n_cores = obj["n_cores"]
        input_feature_type = obj["input_feature_type"]
        mode = obj["mode"]
        use_custom_decimation_func = obj["use_custom_decimation_func"]
        use_conv_stack = obj["use_conv_stack"]
        use_galoss = obj["use_galoss"]

        # --- Logistic output-layer formulation / inhibition loss ---
        # (Sec. 2.2-2.4 of arXiv:2204.08094).
        inhibition_lambda = obj.get("inhibition_lambda", 0.0)
        pairwise_likelihood_path = obj.get("pairwise_likelihood_path", None)
        inhibition_boost = obj.get("inhibition_boost", 1)
        pairwise_likelihood_key = obj.get("pairwise_likelihood_key", None)

    assert input_feature_type == "cqt"
    assert mode == "tab"

    main(mode, input_feature_type, use_custom_decimation_func, use_conv_stack, use_galoss, train_ratio, note_resolution, epoch, lr, seed_, d_model, encoder_heads,
         encoder_layers, n_cores, cqt_n_bins, hop_length, sr,
         inhibition_lambda=inhibition_lambda,
         pairwise_likelihood_path=pairwise_likelihood_path, inhibition_boost=inhibition_boost,
         pairwise_likelihood_key=pairwise_likelihood_key)