# Working in the managed workspace

Ordinary clones of the repository use a standard `.git` directory. No wrapper is
required there. The development workspace used to bootstrap tick-trap restricted
normal `.git` writes, so its local metadata lives in `.tick-trap-git` instead:

```sh
sh scripts/git-local log --oneline
sh scripts/git-local status --short
```

The wrapper selects the alternate metadata if it exists, otherwise normal Git.
In the restricted workspace `tick-trap-history.bundle` is a portable local copy
of the commit history. It is intentionally ignored, not a file distributed with
ordinary clones. It can be restored outside that workspace with:

```sh
git clone tick-trap-history.bundle tick-trap-restored
```

Runtime commands work without dependencies using `PYTHONPATH=src python -m
tick_trap ...`. If the environment blocks writes to uv's default cache, use the
already installed `.venv/bin/python` or a cache under a writable temporary path.

The first GitHub publication used the connected account because terminal network
access was restricted. Its commits were recreated in their original step order;
each published Git tree was checked against the corresponding local tree SHA,
and all remote commit authors were verified as the repository owner. Commit IDs
differ from the original local sequence because server metadata differs. The
original sequence is preserved on the local `original-local-history` branch.
Local `main` follows the exact published commit objects after synchronization.
