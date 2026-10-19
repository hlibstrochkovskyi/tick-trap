"""Small supervised actuator identification study, without confidence claims."""

from dataclasses import replace
from math import fsum, isfinite, sqrt
from random import Random

from .experiments import RunConfig, run
from .numbers import nonnegative, positive, q


def fit_affine(commands, accelerations):
    """Ordinary least squares for acceleration = gain*command+bias."""
    commands, accelerations = list(commands), list(accelerations)
    if len(commands) != len(accelerations) or len(commands) < 2:
        raise ValueError("Identification needs at least two paired observations")
    commands, accelerations = [float(x) for x in commands], [float(x) for x in accelerations]
    if not all(isfinite(x) for x in commands+accelerations):
        raise ValueError("Identification observations must be finite")
    mean_u, mean_y = fsum(commands)/len(commands), fsum(accelerations)/len(accelerations)
    variance = fsum((u-mean_u)**2 for u in commands)
    if variance <= 0:
        raise ValueError("Commands do not excite the actuator gain")
    gain = fsum((u-mean_u)*(y-mean_y) for u, y in zip(commands, accelerations))/variance
    bias = mean_y-gain*mean_u
    return {"gain": gain, "bias": bias,
            "training_rmse": sqrt(fsum((gain*u+bias-y)**2 for u, y in zip(commands, accelerations))/len(commands))}


def learning_study(seed=7, samples=32, noise_std="0.03", plant_gain="0.8", plant_bias="0.1",
                   shifted_gain="0.55", shifted_bias="0.2", run_config=None, methods=None):
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 2:
        raise ValueError("samples must be an integer >=2")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer")
    positive(plant_gain, "plant_gain")
    positive(shifted_gain, "shifted_gain")
    noise_std = float(nonnegative(noise_std, "noise_std"))
    config = RunConfig(**(run_config or {}))
    methods = ["continuous_cbf", "breeden", "zocbf", "exact_hold"] if methods is None else methods
    if not isinstance(methods, list) or not methods:
        raise ValueError("methods must be a nonempty list")
    rng = Random(seed)
    commands = [rng.uniform(-float(q(config.a_max)), float(q(config.a_max))) for _ in range(samples)]
    observations = [float(q(plant_gain))*u+float(q(plant_bias))+rng.gauss(0, noise_std) for u in commands]
    learned = fit_affine(commands, observations)
    if learned["gain"] <= 0:
        raise ValueError("Learned gain is nonpositive; insufficient identification data")
    heldout_rng = Random(seed+1)
    heldout = [heldout_rng.uniform(-float(q(config.a_max)), float(q(config.a_max))) for _ in range(samples)]
    models = {"unit_model": ("1", "0"),
              "learned_model": (str(learned["gain"]), str(learned["bias"]))}
    plants = {"training_distribution": (plant_gain, plant_bias), "shifted_dynamics": (shifted_gain, shifted_bias)}
    evaluation, runs = [], []
    for plant_label, (true_gain, true_bias) in plants.items():
        for model_label, (model_gain, model_bias) in models.items():
            error = [float(q(model_gain))*u+float(q(model_bias))-
                     (float(q(true_gain))*u+float(q(true_bias))) for u in heldout]
            evaluation.append({"plant": plant_label, "model": model_label,
                               "heldout_mean_acceleration_rmse": sqrt(fsum(x*x for x in error)/len(error)),
                               "heldout_max_absolute_error": max(abs(x) for x in error)})
            for method in methods:
                result = run(replace(config, method=method, plant_gain=str(true_gain), plant_bias=str(true_bias),
                                     model_gain=model_gain, model_bias=model_bias, seed=seed))
                result["study_labels"] = {"plant": plant_label, "model": model_label}
                runs.append(result)
    return {"learning_method": "affine ordinary least squares", "seed": seed, "heldout_seed": seed+1,
            "noise_std": noise_std, "training_commands": commands, "training_accelerations": observations,
            "heldout_commands": heldout, "model": learned, "evaluation": evaluation, "runs": runs,
            "interpretation": "Prediction error is measured empirically. No calibrated uncertainty or robust safety guarantee is claimed."}
