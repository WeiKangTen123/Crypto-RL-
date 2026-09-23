TEE Server:

47.250.37.200
root

try ssh -i myserver root@47.250.37.200

-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAWHB51kWa3idnlefUl2ZrO2ow1IM56PparcSl8mLITzwAAAKAHGVQiBxlU
IgAAAAtzc2gtZWQyNTUxOQAAACAWHB51kWa3idnlefUl2ZrO2ow1IM56PparcSl8mLITzw
AAAED83ImEPF+JssHEVLwZTBvmKNxmaAMwHpdwZWolDYR4zRYcHnWRZreJ2eV59SXZms7a
jDUgzno+lqtxKXyYshPPAAAAGnRlZUB0ZWVzLU1hY0Jvb2stUHJvLmxvY2FsAQID
-----END OPENSSH PRIVATE KEY-----






Training:


cd /root/wkang
LD_LIBRARY_PATH=/root/ytee/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib \
PYTHONPATH=/root/wkang \
/root/ytee/.venv/bin/python DRL_BTC/training/train.py --seed 42 2>&1 | tee DRL_BTC/logs/train_s42.log


