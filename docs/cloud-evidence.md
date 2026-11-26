# 华为云证据链（S-02）

截图放到 `evidence/`，本文件只记路径和结果，**不要写 AK/SK/密码**。

## 账号与区域

| 项 | 填写 |
|---|---|
| 区域 | cn-east-3 华东-上海一 |
| 主账号实名 | 是 / 否 |
| 代金券 | 已绑定 / 无 |
| IAM 子用户 | zhixun-a / zhixun-b / zhixun-c |
| 截图 | `evidence/iam-users.png` |

## 网络

| 项 | 填写 |
|---|---|
| VPC | zhixun-vpc `192.168.0.0/16` |
| 子网 | zhixun-subnet `192.168.1.0/24` |
| 安全组 | zhixun-sg |
| 截图 | `evidence/vpc.png` |

## OBS

| 项 | 填写 |
|---|---|
| 桶名 | |
| 是否私有 | 是 |
| 测试对象 | `obs://<bucket>/ping.txt` |
| 截图 | `evidence/obs-put-get.png` |

## RDS

| 项 | 填写 |
|---|---|
| 引擎 | MySQL 8.0 |
| 内网地址 | （只写内网，不写密码） |
| 公网 | 未开启 |
| CRUD 截图 | `evidence/rds-crud.png` |

## Redis

| 项 | 填写 |
|---|---|
| 内网地址 | |
| 公网 | 未开启 |
| 入队出队截图 | `evidence/redis-queue.png` |

## ECS

| 项 | 填写 |
|---|---|
| 规格 / 镜像 | |
| 私有 IP | |
| EIP | 有 / 无（可解绑） |
| SSH 截图 | `evidence/ecs-ssh.png` |

## 码道

| 项 | 填写 |
|---|---|
| 项目名 | 智巡卫士 |
| B 的记录 | `evidence/codearts-b.png` |

## ModelArts

| 项 | 填写 |
|---|---|
| 状态 | 未申请 / 配额中 / 已开通 / W1 用 ECS 容器代替 |
| 说明 | |
