# Pinned original sampled-data experiment inputs

These are unmodified files from Joseph Breeden's
[PhD code repository](https://github.com/jbreeden-um/phd-code), commit
`71982ca53deafe552e3524321e18c1fb1341c865` (3 March 2024), in
`2021/L-CSS CBFs for Sampled Data Systems/Unicycles`.
The repository associates this directory with Breeden, Garg and Panagou,
*Control Barrier Functions in Sampled-Data Systems*, IEEE Control Systems Letters,
6, 367–372, DOI `10.1109/LCSYS.2021.3076127`.

[upstream.json](upstream.json) records original paths, byte sizes, Git blob SHA-1
and SHA-256 for every copied file. It includes the 20 direct MATLAB sources,
five saved one-obstacle runs, the project readme and the upstream license.
Images, symbolic notebooks and the remaining repository are not included.
This is a later repository snapshot, not an assertion that every file is the
exact source used for arXiv v1 or the published figures.

The files retain the original [MIT license and copyright](LICENSE.md). That
license explicitly excludes the papers and preserves external software's own
licenses. No MATLAB code is executed by tick-trap's input reader. Re-running the
original scripts requires their MATLAB/toolbox/OSQP environment, which is not
provided or reproduced here.

The numeric workspace exports are inputs for an independent record audit. Their
saved MATLAB objects are skipped rather than restored. In particular, decoding
samples and commands does not validate nonlinear margin maximizations, solver
residuals, post-solver clipping, fallback branches or continuous safety.
The first saved data column is an initialization call; subsequent columns log
the control applied before the newly saved state. The source integrator's
floating clock and actual exported horizon must also be checked explicitly.

The existing wall-model implementations remain separate specializations of
arXiv `2103.03677v1`. These files do not make that implementation a complete
reproduction of the unicycle or spacecraft experiments.
