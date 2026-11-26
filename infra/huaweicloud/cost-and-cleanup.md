# 费用与清理

默认区域：`cn-east-3`。标签：`project=zhixun` / `env=dev`。

## 预算

- 先用大赛代金券，再动现金。
- 费用中心设预算告警（建议先按代金券额度的 70%）。
- RDS、ECS、EIP 是主要开销；OBS 小文件几乎可忽略；Redis 入门规格通常较低。

## 规格上限（开发期不要升配）

| 资源 | 建议 |
|---|---|
| ECS | 2vCPU，2–4GB，按需 |
| EIP | 按流量或带宽按需，不用就解绑 |
| RDS MySQL | 单机最小 + 40GB |
| DCS Redis | 单机最小内存 |
| OBS | 标准存储，私有桶 |
| ModelArts | W1 不强制开通在线服务 |

## 不用时

1. ECS **关机**（仍可能收盘和 EIP 的钱）。
2. 长时间不做：解绑并释放 EIP。
3. 赛后：按 `project=zhixun` 筛资源，删 ECS → RDS → Redis → 安全组/VPC → OBS 桶（先清空对象）。
4. 删除 IAM 子用户的 Access Key。

## 禁止

- RDS / Redis 对 `0.0.0.0/0` 开放 3306/6379
- 主账号 Access Key 提交进 Git
- 开着 ECS+EIP 过夜却不关机（账单会一直走）
