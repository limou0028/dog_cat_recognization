"""模型：按名字构建，num_classes 可配。

    build_model(name, num_classes, pretrained) -> nn.Module
    set_backbone_trainable(model, trainable)   冻结/解冻除分类头以外的参数
    param_groups(model, lr, backbone_lr_mult)  分类头与 backbone 不同学习率
所有模型的分类头统一命名为 `fc`，便于冻结与分组。
"""
import torch.nn as nn
from torchvision import models as tvm


class SimpleCNN(nn.Module):
    """从零训练的小 CNN：4 个 [Conv-BN-ReLU ×2 + MaxPool] 块 + GAP + FC。
    输入 3×H×W，通道 32→64→128→256，GAP 后 256 维，输出 num_classes。"""

    def __init__(self, num_classes=2, dropout=0.3):
        super().__init__()

        def block(cin, cout):
            return nn.Sequential(
                nn.Conv2d(cin, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
                nn.Conv2d(cout, cout, 3, padding=1, bias=False), nn.BatchNorm2d(cout), nn.ReLU(inplace=True),
                nn.MaxPool2d(2),
            )

        self.features = nn.Sequential(block(3, 32), block(32, 64), block(64, 128), block(128, 256))
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(256, num_classes)

    def forward(self, x):
        x = self.pool(self.features(x)).flatten(1)
        return self.fc(self.dropout(x))


def build_model(name, num_classes=2, pretrained=True):
    name = name.lower()
    if name == "simple_cnn":
        return SimpleCNN(num_classes)
    if name in ("resnet18", "resnet34", "resnet50"):
        weights = {"resnet18": tvm.ResNet18_Weights.IMAGENET1K_V1,
                   "resnet34": tvm.ResNet34_Weights.IMAGENET1K_V1,
                   "resnet50": tvm.ResNet50_Weights.IMAGENET1K_V2}[name] if pretrained else None
        m = getattr(tvm, name)(weights=weights)
        m.fc = nn.Linear(m.fc.in_features, num_classes)
        return m
    raise ValueError(f"未知模型: {name}")


def head_params(model):
    return list(model.fc.parameters())


def backbone_params(model):
    head = {id(p) for p in head_params(model)}
    return [p for p in model.parameters() if id(p) not in head]


def set_backbone_trainable(model, trainable: bool):
    for p in backbone_params(model):
        p.requires_grad = trainable


def param_groups(model, lr, backbone_lr_mult=1.0):
    return [
        {"params": head_params(model), "lr": lr},
        {"params": backbone_params(model), "lr": lr * backbone_lr_mult},
    ]


def count_params(model):
    return sum(p.numel() for p in model.parameters())
