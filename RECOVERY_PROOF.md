# Retry-safe compilation proof

- Contract: https://explorer-studio.genlayer.com/address/0x79a3ED7caEC5762aD4C283E663cbde6c51948724
- Deployment: https://explorer-studio.genlayer.com/tx/0x562a0a3ead95d4e5231ca032ac2bec1cfd331a735390fe7207673ff3911f4f3a
- Version 1 compilation: https://explorer-studio.genlayer.com/tx/0x5bd1ab2b6bcdd482b960230379bcde28ff9d3656c866c5e05cc6ec6d9d3d974d
- Version 2 abandoned attempt: https://explorer-studio.genlayer.com/tx/0xdd3a9a26741999082919ecdb76f6dd9f84c269a616bdadcc85fa3dde0a3b4b57
- Corrected version 2 submission: https://explorer-studio.genlayer.com/tx/0x0c5dd190ab5b690e291c32dcc02c38659d39ae0439032f599db9c214ecb34577
- Corrected version 2 compilation: https://explorer-studio.genlayer.com/tx/0x60106ed2170e826dbc60cbe6f6c72a5c36947695f085d296c8db2c638ae48d1a

The immutable first attempt stores `version=2`, `attempt=1`, `state=ABANDONED`, and `parent_plan=retry-v1`. The replacement stores `version=2`, `attempt=2`, `replacement_of=retry-v2-abandoned`, `state=COMPILED`, and the same active parent. The intent stores `reserved_version=2`, `active_plan=retry-v2-corrected`, and `state=COMPILED`. `get_latest_attempt("retry-proof", 2)` returns the corrected attempt.

Explorer source exactly matches `contracts/AgentIntentCompiler.py`, SHA-256 `c23c91607ed30a964d77f825458d3efa5880554227e4057943672786c622fef6`.
