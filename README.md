# EvFrame - 高策略性RPG复杂事件处理框架

![Python Version](https://img.shields.io/badge/Python-3.8%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

## 概述

EvFrame 是一个专为复杂策略性RPG设计的模块化事件处理框架。它通过**分阶段事件处理**、**自定义修饰器**和**动态监听器**机制，实现了对嵌套事件、连锁反应和动态逻辑修改的深度支持。其核心设计理念是"事件即消息"，所有游戏逻辑（如攻击、治疗、技能效果）均通过消息传递实现，为开发者提供了极高的灵活性和扩展性。

---

## 核心特性

### 1. 事件分阶段处理
采用 **PRE-MAIN-POST** 三阶段模型：
```python
class MessagePhase(Enum):
    PRE = auto()   # 预处理（如伤害计算前修改基础值）
    MAIN = auto()  # 主处理（实际生效逻辑）
    POST = auto()  # 后处理（结果回调与连锁触发）
```

- **NONE** 类型消息自动拆分为三阶段
- 支持阶段间数据继承与校验
- 示例：攻击事件自动生成 `DAMAGE` 消息，并在不同阶段应用暴击/闪避计算

### 2. 自定义修饰器系统

通过 `modify()` 方法动态修改事件参数：

```python
# 测试用例：技能A在DAMAGE预处理阶段增加伤害
class SkillA(PassiveSkill):
    def effect(self, msg: GameMessage):
        if msg.type == "DAMAGE" and msg.phase == MessagePhase.PRE:
            msg.modify(('set_value', lambda x: x.get_value() + 10))  # 修饰器修改伤害值
```

#### 修饰器类型

| 类型         | 功能                        | 示例          |
| :----------- | :-------------------------- | :------------ |
| set_value    | 修改事件数值                | 伤害增益/减益 |
| set_sender   | 修改事件发起者              | 伤害反弹      |
| set_receiver | 修改事件目标                | 转移治疗目标  |
| 自定义       | 通过`register_modifier`注册 | 复杂连锁逻辑  |

### 3. 动态监听器机制

通过继承 `PassiveSkill` 实现事件监听：

```python
# 测试用例：荆棘护甲反弹伤害
class ThornArmorSkill(PassiveSkill):
    def effect(self, msg):
        if msg.type == "DAMAGE" and msg.phase == MessagePhase.PRE:
            reflect_msg = msg.create(...)  # 创建新DAMAGE消息
            msg.messagechain.i.manager.acceptmsgp(reflect_msg)  # 注入新事件
```

#### 监听器优势

- **自动注册**：通过 `manager.register()` 实现零配置监听
- **上下文感知**：可通过 `msg.phase` 精确控制触发时机
- **嵌套支持**：事件处理中生成的新事件自动进入队列

------

## 复杂逻辑适应性

### 案例1：多重技能连锁

```bash
# test_complex_skills_interaction 测试流程：
1. 角色1发起攻击（原始伤害20）
2. 技能A（PRE阶段）：伤害+10 → 30
3. 技能B（PRE阶段）：注册自定义修饰器，伤害减半为15，反弹15
4. 主处理：角色2受到15伤害
5. POST阶段：技能C治疗角色2（+2 HP）
6. 反弹伤害触发：角色1受到15伤害
7. POST阶段：技能C再次治疗角色1（+2 HP）
```

▶️ **最终结果**：角色1/2实际各损失13 HP，框架自动处理了4层事件嵌套

### 案例2：动态修饰器注册

```python
# 技能B通过临时注册修饰器实现复杂逻辑
class SkillB(PassiveSkill):
    def effect(self, msg):
        def custom_modifier(...):
            # 动态计算伤害分配
            msg.value = reduced
            reflect_msg = msg.create(...)  # 生成反弹事件
            msg.messagechain.i.manager.acceptmsgp(reflect_msg)
            return raw_value, reduced, True
        msg.modify(('SkillB_custom_modifier',0))  # 绑定临时修饰器
```

------

## 扩展性设计

### 1. 模块化处理器

```python
class Handler:
    def register_type(self, msg_type: str, handler: Callable, phase: MessagePhase)
    def replace_type(self, msg_type: str, handler: Callable, phase: MessagePhase)
    def handles(self, msg_type: str, phase: MessagePhase)  # 装饰器模式
```

- 支持继承（如 `Mainhandler=Handler(BASE_MSG_HANDLER)`）
- 内置攻击/伤害/治疗等基础事件处理器

### 2. 消息链管理

```python
class MessageChain:
    def acceptmsg(self, msg)   # 左插入（立即执行）
    def acceptmsgp(self, msg)  # 右插入（延迟执行）
```

- 自动处理NONE消息拆分
- 记录已响应对象防止循环

### 3. 消息元数据

通过 `MessageExtra` 枚举实现强类型扩展：

```python
class MessageExtra(Enum):
    DAMAGE_TYPE = ("damage_type", str)        # 伤害类型标记
    AFTER_CRIT_DAMAGE = ("after_crit_damage", int)  # 暴击后伤害
    RAW_VALUE = ("raw_value", Any)           # 原始值追踪
```