"""Trim a pairwise-likelihood / inhibition matrix that was estimated on a
guitar with more fret classes down to this codebase's expected geometry
(6 strings x 21 fret classes), and realign it to this codebase's class
ordering.

Two conventions are involved here, and they differ:

1. The *official* inhibition-matrix trainer's convention (as pasted by the
   user, matching amt_tools): within each string's block of classes,
   index 0 is "silence" ("not played"), and indices 1..num_pitches are
   frets in ascending order. `trim_inhibition_matrix_official` below is a
   faithful port of that trimming logic: it just keeps the first
   `num_pitches + int(silence_activations)` classes per string, dropping
   the higher, unused fret classes off the end.

2. *This* codebase's convention (see visualize.py / predict.py, which both
   check `fret != 20` / `argmax_index < 20` on a 21-class axis): within
   each string's block of 21 classes, indices 0..19 are frets in ascending
   order, and index 20 (the LAST index) is "not played" / silence.

Naively using the officially-trimmed matrix directly with this codebase's
`InhibitionLoss` would silently misalign every pairwise weight (it would
happily run -- shapes would match -- but would treat the wrong string/fret
combination as "silence", which is a much worse failure mode than a shape
error). `realign_silence_to_last` fixes this by rotating the silence class
from the front to the back of each string's block.

Typical usage
-------------
    python trim_inhibition_matrix.py \
        --in my_inhibition_matrix.npz \
        --key inhibition_weights \
        --num-pitches 20 \
        --silence-activations \
        --source-silence-position first \
        --out pairwise_likelihood_trimmed.npz

If your source matrix already follows this codebase's silence-last
convention (unlikely if it came from the same trainer as the pasted
snippet, but possible if you built it yourself), pass
`--source-silence-position last` to skip the realignment step.
"""
import argparse

import numpy as np


def _load_matrix(path, key=None):
    if path.endswith(".npz"):
        with np.load(path) as npz:
            keys = list(npz.keys())
            if key is not None:
                if key not in keys:
                    raise KeyError(f"key {key!r} not found in {path!r}; available keys: {keys}")
                return npz[key]
            if len(keys) == 1:
                return npz[keys[0]]
            raise ValueError(
                f"{path!r} contains multiple arrays {keys}; pass --key to pick one")
    return np.load(path)


def trim_inhibition_matrix_official(inhibition_matrix, num_strings, num_pitches,
                                     silence_activations=False):
    """Faithful port of the original inhibition-matrix trainer's trim
    function. Assumes silence (if present) is class index 0 within each
    string's block, with frets ascending after it (indices 1..num_pitches);
    trims away the higher, unused fret classes past `num_pitches`.

    Parameters
    ----------
    inhibition_matrix : ndarray (N x N)
        Matrix of inhibitory weights for string/fret pairs.
        N - number of unique string/fret activations (untrimmed).
    num_strings : int
        Number of strings to expect in the inhibition matrix.
    num_pitches : int
        Number of pitches per string to expect in the inhibition matrix.
    silence_activations : bool
        Whether the silent string is explicitly modeled as an activation.

    Returns
    ----------
    inhibition_matrix : ndarray (M x M)
        Matrix of inhibitory weights for string/fret pairs, silence
        (if present) still at index 0 of each string's block.
        M - number of unique string/fret activations (trimmed).
    """
    # Determine how many classes were originally included in the matrix
    num_classes_ = inhibition_matrix.shape[-1] // num_strings
    # Temporarily re-shape the matrix to be 4D
    inhibition_matrix = np.reshape(inhibition_matrix, (num_strings, num_classes_,
                                                         num_strings, num_classes_))

    # Determine how many classes are to be in the new matrix
    num_classes = num_pitches + int(silence_activations)
    # Throw away any extraneous frets
    inhibition_matrix = inhibition_matrix[:, :num_classes, :, :num_classes]
    # Calculate output dimensionality
    num_activations = num_strings * num_classes
    # View the matrix as a square (2D) again
    inhibition_matrix = np.reshape(inhibition_matrix, (num_activations, num_activations))

    return inhibition_matrix


def realign_silence_to_last(inhibition_matrix, num_strings, num_classes):
    """Rotate the silence class from index 0 to index (num_classes - 1)
    within each string's block, converting a silence-first matrix (the
    official trainer's convention) into this codebase's silence-last
    convention (used by TabEstimator / InhibitionLoss).

    Parameters
    ----------
    inhibition_matrix : ndarray (N x N), N = num_strings * num_classes
        Matrix with silence at index 0 of each string's block.
    num_strings : int
    num_classes : int
        Classes per string (e.g. 21 = 20 frets + silence).

    Returns
    ----------
    inhibition_matrix : ndarray (N x N)
        Matrix with silence moved to index (num_classes - 1) of each
        string's block; fret ordering among the remaining classes is
        otherwise unchanged.
    """
    C = num_strings * num_classes
    assert inhibition_matrix.shape == (C, C)

    # build the per-block permutation [1, 2, ..., num_classes-1, 0], i.e.
    # move index 0 (silence) to the end, then tile it across strings with
    # the correct offsets
    block_perm = np.roll(np.arange(num_classes), -1)
    perm = np.concatenate([s * num_classes + block_perm for s in range(num_strings)])

    return inhibition_matrix[np.ix_(perm, perm)]


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--in", dest="in_path", type=str, required=True,
                         help="path to the source .npy or .npz inhibition matrix")
    parser.add_argument("--key", type=str, default=None,
                         help="array name within the source .npz, if it has more than one array")
    parser.add_argument("--num-strings", type=int, default=6)
    parser.add_argument("--num-pitches", type=int, default=20,
                         help="number of playable fret classes per string to keep (default 20, "
                              "matching this codebase's 20 frets + 1 silence = 21 classes)")
    parser.add_argument("--silence-activations", action="store_true", default=True,
                         help="whether the source matrix models silence as an explicit "
                              "activation (default True)")
    parser.add_argument("--no-silence-activations", dest="silence_activations",
                         action="store_false")
    parser.add_argument("--source-silence-position", choices=["first", "last"], default="first",
                         help="where silence sits within each string's block in the SOURCE "
                              "matrix: 'first' (index 0, the official trainer's convention -- "
                              "default) or 'last' (already matches this codebase, no "
                              "realignment needed)")
    parser.add_argument("--out", type=str, required=True,
                         help="output .npz path")
    parser.add_argument("--out-key", type=str, default="weights",
                         help="array name to save the trimmed matrix under (default 'weights')")
    args = parser.parse_args()

    matrix = _load_matrix(args.in_path, key=args.key)
    print(f"loaded matrix {matrix.shape} from {args.in_path}")

    trimmed = trim_inhibition_matrix_official(
        matrix,
        num_strings=args.num_strings,
        num_pitches=args.num_pitches,
        silence_activations=args.silence_activations,
    )
    print(f"trimmed to {trimmed.shape} "
          f"(silence at index 0 of each string's block, per source convention)")

    num_classes = args.num_pitches + int(args.silence_activations)
    if args.silence_activations and args.source_silence_position == "first":
        trimmed = realign_silence_to_last(trimmed, num_strings=args.num_strings,
                                           num_classes=num_classes)
        print(f"realigned silence to index {num_classes - 1} of each string's block "
              f"(this codebase's convention)")
    else:
        print("skipped realignment (source already silence-last, or no silence class present)")

    np.savez(args.out, **{args.out_key: trimmed})
    print(f"saved to {args.out} (key={args.out_key!r})")


if __name__ == "__main__":
    main()



# Run this command  to get pairwise_likelihood_trimmed.npz matrix
# !python src/trim_inhibition_matrix.py \
#   --in "/content/src/your_144_matrix.npz" \
#   --num-pitches 20 \
#   --silence-activations \
#   --source-silence-position first \
#   --out "/content/src/pairwise_likelihood_trimmed.npz"