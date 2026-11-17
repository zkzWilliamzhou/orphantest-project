# Demo fixture

Four test files. `orphantest.json` declares one command that only reaches `test_math.py`.
Two test modules and one legacy file never appear in the execution ledger.

```
orphantest --root examples/demo_repo --config examples/demo_repo/orphantest.json \
  audit --execute --trust-config
```

Swap the config to `orphantest.reconciled.json` to reconcile the ledger.
