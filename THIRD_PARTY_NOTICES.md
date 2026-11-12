# Third-Party Notices

本项目代码使用 MIT LICENSE；以下第三方数据/库按其各自许可证使用。

## 数据集

- **NVIDIA PhysicalAI-WorldModel-Synthetic-Warehouse-Operations-Scenes**
  - 来源：<https://huggingface.co/datasets/nvidia/PhysicalAI-WorldModel-Synthetic-Warehouse-Operations-Scenes>
  - 许可：**OpenMDW-1.1**（当前数据集卡；早期 revision 曾标 CC BY 4.0）
  - 用途：近失场景 metadata 索引、检测/跟踪/轨迹实验的合成数据
  - 注意：合成数据，不代表真实工厂；不下载全量 549 GiB，只取清单涉及的 shard

## 计划使用的开源库（安装时遵循其许可证）

| 组件 | 用途 | 许可 |
|---|---|---|
| MMDetection / RTMDet | 人员/叉车检测基线（A-02） | Apache-2.0 |
| ByteTrack | 多目标跟踪（A-03） | MIT |
| PyTorch | 模型训练/推理 | BSD-3-Clause |
| pandas | metadata 处理 | BSD-3-Clause |
| pyarrow | parquet 读写 | Apache-2.0 |
| Pydantic | S-01 Schema/校验 | MIT |
| pytest | 测试 | MIT |

> 以上库尚未全部 vendored；实际安装/分发时以其 release 的 LICENSE 为准。若后续引入 Social-STGCNN 等参考实现，需单独登记其 MIT 许可与来源。
