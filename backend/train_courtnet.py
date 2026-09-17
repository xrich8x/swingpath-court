"""Fine-tune the court-keypoint model (CourtNet) on OUR calibrated clips.

Transfer learning from the broadcast-trained checkpoint (weights/court_detector.pt)
to the amateur angles in ../data/court_dataset (built by build_court_dataset.py).
The core augmentation is RANDOM PERSPECTIVE: every sample is re-warped as if shot
from a different camera angle (corner jitter -> homography warp of image AND
keypoints), so each user court-setup teaches a whole neighbourhood of angles, not
one. Horizontal flips swap the left/right keypoint identities.

    .venv-train/Scripts/python.exe train_courtnet.py --epochs 15
Best checkpoint -> weights/courtnet_ft.pt (calibration.detect_court_learned
prefers it automatically when present; the reprojection gate still applies).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

import cv2
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from swingvision._courtnet import CourtNet

IN_W, IN_H = 640, 360
SIGMA = 7.0
# Horizontal flip swaps left/right keypoint identities (order: COURT_KP_LANDMARKS).
FLIP_MAP = [1, 0, 3, 2, 6, 7, 4, 5, 9, 8, 11, 10, 12, 13]


def heatmaps(kps, w=IN_W, h=IN_H, sigma=SIGMA):
    """15 target heatmaps: 14 keypoints + court centre (mean of the 4 corners)."""
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    out = np.zeros((15, h, w), dtype=np.float32)
    pts = list(kps) + [np.mean(kps[:4], axis=0)]
    for i, (x, y) in enumerate(pts):
        if not (-40 <= x < w + 40 and -40 <= y < h + 40):
            continue
        out[i] = np.exp(-((xs - x) ** 2 + (ys - y) ** 2) / (2 * sigma * sigma))
    return out


SPLIT_MANIFEST = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "data", "gold", "court_split.json")


def court_test_clips(manifest=SPLIT_MANIFEST) -> list[str]:
    """The clips declared TEST in data/gold/court_split.json.

    Derived from the manifest rather than a --exclude flag: CLAUDE.md records that
    the ball trainer's old `--exclude indoor_elev` default matched no directory at
    all and "had been protecting nothing". A guard nobody has to remember to pass
    is the only kind that holds.
    """
    with open(manifest, "r", encoding="utf-8") as f:
        return sorted(json.load(f)["test"]["clips"])


def assert_no_court_gold_leak(root, manifest=SPLIT_MANIFEST) -> list[str]:
    """Refuse to train if a TEST clip is present in the training root.

    This is why the guard exists: before it, 17 of the 20 hand-labelled court gold
    clips were also in data/court_dataset/, so every figure in
    data/gold/court_scores.md measured the model on its own training data. Refuse,
    do not warn — a silent leak is exactly what produced that table.
    """
    test = set(court_test_clips(manifest))
    present = {t for t in os.listdir(root)
               if os.path.isfile(os.path.join(root, t, "labels.json"))}
    leaks = sorted(test & present)
    if leaks:
        lines = "\n".join(f"    {t}" for t in leaks)
        raise SystemExit(
            "REFUSING TO TRAIN: these dirs are declared TEST in "
            f"data/gold/court_split.json but are present in {root}:\n{lines}\n"
            "Their hand-labelled court gold is the BENCHMARK. Training on them "
            "would make every court number a measurement of the model on its own "
            "training data — which is the situation this split was created to end. "
            "Move the dirs out of the training root, or change the split "
            "deliberately (it is one-way, and it invalidates prior checkpoints).")
    missing = sorted(test - present)
    return missing


class CourtFrames(Dataset):
    def __init__(self, root, split="train", val_frac=0.2, augment=True,
                 balance_to=60, exclude=()):
        # Balance domains: each clip is repeated up to ~balance_to training frames
        # so a big single-calibration clip (indoor_elev, 222) can't drown the small
        # hand-labelled amateur clips (~15 each), and broadcast isn't forgotten.
        # Random-perspective augmentation turns the repeats into distinct samples.
        self.samples = []
        self.augment = augment and split == "train"
        exclude = set(exclude)
        for tag in sorted(os.listdir(root)):
            lp = os.path.join(root, tag, "labels.json")
            if not os.path.isfile(lp):
                continue
            if tag in exclude:      # declared TEST — never a training sample
                continue
            meta = json.load(open(lp))
            items = sorted(((int(k), v) for k, v in meta["labels"].items()))
            n_val = max(1, int(len(items) * val_frac))
            keep = items[:-n_val] if split == "train" else items[-n_val:]
            reps = max(1, round(balance_to / max(1, len(keep)))) if split == "train" else 1
            for idx, kps in keep:
                for _ in range(reps):
                    self.samples.append((os.path.join(root, tag), idx, np.asarray(kps, np.float32)))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, k):
        d, i, kps = self.samples[k]
        img = cv2.imread(os.path.join(d, f"{i:05d}.jpg"))
        kps = kps.copy()

        if self.augment:
            if random.random() < 0.5:   # horizontal flip + identity swap
                img = cv2.flip(img, 1)
                kps[:, 0] = IN_W - 1 - kps[:, 0]
                kps = kps[FLIP_MAP]
            if random.random() < 0.6:   # random perspective = new camera angle
                j = IN_W * 0.05
                src = np.float32([[0, 0], [IN_W, 0], [IN_W, IN_H], [0, IN_H]])
                dst = src + np.random.uniform(-j, j, (4, 2)).astype(np.float32)
                P = cv2.getPerspectiveTransform(src, dst)
                img = cv2.warpPerspective(img, P, (IN_W, IN_H))
                ones = np.ones((len(kps), 1), np.float32)
                q = (P @ np.hstack([kps, ones]).T).T
                kps = (q[:, :2] / q[:, 2:3]).astype(np.float32)
            if random.random() < 0.5:   # lighting jitter
                a = 1.0 + random.uniform(-0.3, 0.3)
                b = random.uniform(-25, 25)
                img = cv2.convertScaleAbs(img, alpha=a, beta=b)

        inp = np.rollaxis(img.astype(np.float32) / 255.0, 2, 0)
        return torch.from_numpy(np.ascontiguousarray(inp)), torch.from_numpy(heatmaps(kps)), torch.from_numpy(kps)


def evaluate(model, loader, device):
    model.eval()
    errs = []
    with torch.no_grad():
        for inp, _, kps in loader:
            out = torch.sigmoid(model(inp.to(device)))
            B = out.shape[0]
            hm = out.reshape(B, 15, IN_H, IN_W)[:, :14]
            flat = hm.reshape(B, 14, -1).argmax(dim=2).cpu()
            px = (flat % IN_W).float()
            py = (flat // IN_W).float()
            e = torch.hypot(px - kps[:, :, 0], py - kps[:, :, 1])
            vis = (kps[:, :, 0] >= 0) & (kps[:, :, 0] < IN_W) & (kps[:, :, 1] >= 0) & (kps[:, :, 1] < IN_H)
            errs += e[vis].tolist()
    errs = np.asarray(errs)
    return float(np.median(errs)), float((errs <= 8).mean())


def hms(seconds: float) -> str:
    """Compact wall-clock. Duplicated from train_ballnet rather than shared:
    the two trainers are deliberately independent scripts, and a dozen lines of
    formatting is a cheaper price than a coupling between them."""
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}h{m:02d}m" if h else (f"{m}m{s:02d}s" if m else f"{s}s")


def emit(**fields) -> None:
    """One machine-readable line per epoch, for tools/lab_server.py."""
    print("LABJSON:" + json.dumps(fields), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/court_dataset")
    ap.add_argument("--epochs", type=int, default=15)
    ap.add_argument("--batch", type=int, default=6)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--init", default="weights/court_detector.pt")
    ap.add_argument("--out", default="weights/courtnet_ft.pt")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--freeze-encoder", action="store_true", dest="freeze_encoder",
                    help="train the decoder only (v1 recipe; too conservative alone)")
    ap.add_argument("--seed", type=int, default=0,
                    help="PAIRS AN A/B, same discipline as train_ballnet.py's --seed. "
                         "Without this, two arms differ by init, shuffle order and "
                         "augmentation draws as well as by the flag under test, so a "
                         "small effect can't be attributed to the flag.")
    args = ap.parse_args()

    # Not bit-determinism: cuDNN picks conv algorithms nondeterministically and
    # forcing otherwise costs real time. This pairs the things that dominate a short
    # run — the init and the order the data (and augmentation) arrives in.
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)

    # The split is enforced twice, on purpose. assert_no_court_gold_leak refuses to
    # start if a TEST clip sits in the training root at all; the `exclude` below
    # keeps it out of the sample list even if someone later loosens the first check.
    test_clips = court_test_clips()
    missing = assert_no_court_gold_leak(args.data)
    print(f"court split: {len(test_clips)} TEST clips held out "
          f"({len(missing)} of them are not in {args.data} at all)")
    if missing:
        print(f"  not present (nothing to exclude): {', '.join(missing)}")

    train_ds = CourtFrames(args.data, "train", exclude=test_clips)
    val_ds = CourtFrames(args.data, "val", augment=False, exclude=test_clips)
    # NOTE: `val` here is the last 20% of FRAMES of each training clip, not a
    # held-out clip. It is an early-stopping signal, not a benchmark — the
    # benchmark is tools/eval_court.py over the TEST clips.
    print(f"train {len(train_ds)} / val {len(val_ds)} | device {args.device}")
    train_ld = DataLoader(train_ds, batch_size=args.batch, shuffle=True, num_workers=2,
                          generator=torch.Generator().manual_seed(args.seed),
                          pin_memory=(args.device == "cuda"))
    val_ld = DataLoader(val_ds, batch_size=args.batch, num_workers=2)

    model = CourtNet(out_channels=15)
    model.load_state_dict(torch.load(args.init, map_location="cpu"))
    model.to(args.device)
    # Optionally freeze the encoder (v1 recipe — proved too conservative on its
    # own). Default: all params trainable at a LOW lr (v2), relying on the
    # broadcast oversampling to prevent the forgetting that broke v0.
    frozen = 0
    if args.freeze_encoder:
        for name, p in model.named_parameters():
            if any(name.startswith(f"conv{i}.") for i in range(1, 11)):
                p.requires_grad = False
                frozen += 1
    print(f"frozen encoder params: {frozen}")
    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(trainable, lr=args.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=args.epochs)
    # MSE on sigmoid heatmaps — the regime the checkpoint was originally trained
    # in; positives up-weighted so the loss doesn't collapse to all-background.
    def crit(logits, target):
        prob = torch.sigmoid(logits)
        w = 1.0 + 20.0 * target
        return (w * (prob - target) ** 2).mean()

    med0, hit0 = evaluate(model, val_ld, args.device)
    print(f"BEFORE fine-tune: val median {med0:.1f}px  within8px {hit0*100:.1f}%")

    best = hit0
    t_start = time.time()
    emit(kind="start", epochs=args.epochs, out=args.out, device=args.device,
         baseline_median_px=round(med0, 2), baseline_hit8=round(hit0 * 100, 2))
    for ep in range(1, args.epochs + 1):
        t_ep = time.time()
        model.train()
        tot = 0.0
        for inp, hm, _ in train_ld:
            inp, hm = inp.to(args.device), hm.to(args.device)
            opt.zero_grad()
            out = model(inp).reshape(hm.shape)
            loss = crit(out, hm)
            loss.backward()
            opt.step()
            tot += float(loss.detach())
        sched.step()
        med, hit = evaluate(model, val_ld, args.device)
        mark = ""
        if hit > best:
            best = hit
            torch.save(model.state_dict(), args.out)
            mark = "  <- saved"
        ep_s = time.time() - t_ep
        eta = ep_s * (args.epochs - ep)
        loss = tot / max(len(train_ld), 1)
        print(f"epoch {ep:3d}  loss {loss:.4f}  "
              f"val median {med:.1f}px  within8px {hit*100:.1f}%{mark}"
              f"   [{hms(ep_s)}/epoch, eta {hms(eta)}]", flush=True)
        emit(kind="epoch", epoch=ep, epochs=args.epochs, loss=round(loss, 5),
             median_px=None if med != med else round(med, 2),
             hit8=round(hit * 100, 2), saved=bool(mark),
             epoch_s=round(ep_s, 1), elapsed_s=round(time.time() - t_start, 1),
             eta_s=round(eta, 1))
    total = time.time() - t_start
    print(f"best within-8px: {best*100:.1f}% (started {hit0*100:.1f}%) -> {args.out}"
          f"   (total {hms(total)})")
    emit(kind="final", best=round(best * 100, 2), baseline=round(hit0 * 100, 2),
         out=args.out, total_s=round(total, 1))


if __name__ == "__main__":
    main()
