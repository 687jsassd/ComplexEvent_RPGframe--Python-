# basegameclasses.py
"""
# Author: assd687
# Version: 0.0.15a
# Description: Base classes of RPG.(Skills,Character,Items etc.)
# Date: 2025-06-06
"""
from __future__ import annotations
from typing import List, TYPE_CHECKING, Any, Optional
from abc import ABC
from dataclasses import dataclass
import uuid
if TYPE_CHECKING:
    from evframe import GameMessage, Handler  # 仅用于类型检查

# 技能部分(待补充)


@dataclass
class BasicSkillAttributes:
    """
    该数据类用于存储技能的基本属性。
    包含技能的名称、描述以及技能的拥有者。
    """
    name: str
    owner: 'Character'  # 拥有者
    description: Optional[str] = None


class Skill(ABC):
    """
    技能类，作为所有技能的抽象基类。
    该类定义了技能的基本属性和方法，包括初始化、技能效果实现以及注册技能等功能。
    所有具体的技能类都应继承自此类并实现 `effect` 方法。
    """

    def __init__(self, attributes: BasicSkillAttributes):
        self.attributes = attributes
        self.uuid = uuid.uuid4()
        self.reg_type = f"SKILL_{self.__class__.__name__.upper()}"
        self._api = SkillAPI(self)  # API接口

    def effect(self, msg: 'GameMessage') -> Any:
        """技能效果实现"""

    def reg(self, handler: 'Handler'):
        """注册技能"""
        handler.register_type(self.reg_type, self.effect)

    @property
    def i(self):
        """api接口"""
        return self._api


class ActiveSkill(Skill):
    """
    主动技能类，继承自 Skill 抽象基类。
    该类用于表示需要主动触发的技能，包含主动技能效果实现和触发技能效果的方法。
    所有具体的主动技能类都应继承自此类。
    """

    def effect(self, msg: 'GameMessage', *args: Any, **kwargs: Any) -> Any:
        """主动技能效果实现"""

    def trigger(self, msg: 'GameMessage', *args: Any, **kwargs: Any) -> Any:
        """触发技能效果"""
        return self.effect(msg, *args, **kwargs)


class PassiveSkill(Skill):
    """
    被动技能类，继承自 Skill 抽象基类。
    该类用于表示无需主动触发，会自动生效的技能，包含被动技能效果实现和效果更新的方法。
    所有具体的被动技能类都应继承自此类。
    """

    def effect(self, msg: 'GameMessage') -> Any:
        """被动技能效果实现"""

    def update(self, msg: 'GameMessage') -> bool:
        """被动技能效果更新"""
        return self.effect(msg)


class SkillAPI:
    """
    技能 API 类，用于提供对技能属性的访问接口。
    该类封装了技能对象的各种属性，通过属性装饰器提供只读访问，
    确保技能属性的访问更加安全和规范。
    """

    def __init__(self, skill: Skill) -> None:
        self.skill = skill
        self.attributes = skill.attributes
        self._name = skill.attributes.name
        self._description = skill.attributes.description
        self._owner = skill.attributes.owner
        self._uuid = skill.uuid
        self._reg_type = skill.reg_type
    #

    @property
    def name(self):
        """
        技能名称属性。
        """
        return self._name

    @property
    def description(self):
        """
        技能描述属性。
        """
        return self._description

    @property
    def owner(self):
        """
        技能拥有者。
        """
        return self._owner

    @property
    def uuid(self):
        """
        技能的唯一标识符。
        """
        return self._uuid

    @property
    def reg_type(self):
        """
        技能的注册类型。
        """
        return self._reg_type

# 物品部分(待补充)


@dataclass
class BasicItemAttributes:
    """
    该数据类用于存储物品的基本属性。
    包含物品的名称和描述。
    """
    name: str
    description: str


class Item(ABC):
    """
    物品类，作为所有物品的抽象基类。
    该类定义了物品的基本属性和方法，所有具体的物品类都应继承自此类。
    物品的基本属性通过 `BasicItemAttributes` 类存储。
    """

    def __init__(self, attributes: BasicItemAttributes):
        self.attributes = attributes
        self._api = ItemAPI(self)  # API接口

    @property
    def i(self):
        """
        物品的 API 接口。
        """
        return self._api


class ItemAPI:
    """
    物品 API 类，用于提供对物品属性的访问接口。
    该类封装了物品对象的各种属性，通过属性装饰器提供只读访问，
    确保物品属性的访问更加安全和规范。
    """

    def __init__(self, item: Item) -> None:
        self.item = item
        self.attributes = item.attributes
        self._name = item.attributes.name
        self._description = item.attributes.description

    @property
    def name(self):
        """物品名称属性"""
        return self._name

    @property
    def description(self):
        """物品描述属性"""
        return self._description

# 角色部分


@dataclass
class BasicCharacterAttributes:
    """
    该数据类用于存储角色的基本属性。
    包含角色的名称、等级、经验值、生命值、魔法值、攻击力、防御力等各项属性。
    """
    name: str

    level: int = 1  # 等级
    exp: int = 0  # 经验

    max_hp: int = 100  # 最大生命值
    current_hp: int = 100  # 当前生命值
    max_mp: int = 100  # 最大魔法值
    current_mp: int = 100  # 当前魔法值

    attack: int = 10  # 攻击力
    defense: int = 10  # 防御力
    magic_attack: int = 10  # 魔法攻击力
    magic_defense: int = 10  # 魔法防御力
    speed: int = 10  # 速度
    accuracy: int = 100  # 命中率
    evasion: int = 5  # 闪避率
    critical: int = 5  # 暴击率
    critical_damage: int = 200  # 暴击伤害
    luck: int = 0  # 幸运

    team: int = 0  # 队伍


class Character(ABC):
    """
    角色类，作为所有角色的抽象基类。
    该类定义了角色的基本属性和方法，包括初始化角色的基本属性、技能列表和物品列表，
    提供角色属性的 API 访问接口，以及角色信息的字符串表示方法等。
    所有具体的角色类都应继承自此类。
    """

    def __init__(self,
                 attributes: BasicCharacterAttributes,
                 skills: Optional[List[Skill]] = None,
                 items: Optional[List[Item]] = None,):
        self.attributes = attributes
        # 显式初始化
        self.skills: List[Skill] = skills if skills is not None else list()
        # 显式初始化
        self.items: List[Item] = items if items is not None else list()
        self._api = CharacterAPI(self)  # API接口

    @property
    def i(self):
        """api接口"""
        return self._api

    def __str__(self):
        return f"{self.i.name}({self.i.team})"

    def __repr__(self):
        return f"{self.attributes},skills:{self.skills},items:{self.items},team:{self.i.team}"


class CharacterAPI:
    """
    角色 API 类，用于提供对角色属性的访问接口。
    该类封装了角色对象的各种属性，通过属性装饰器提供访问，
    同时提供修改角色属性的方法，并确保属性值的合法性。
    包含角色基本属性、技能列表、物品列表的访问，以及属性修改和检查方法。
    """
    name: str
    level: int
    exp: int
    max_hp: int
    current_hp: int
    max_mp: int
    current_mp: int
    attack: int
    defense: int
    magic_attack: int
    magic_defense: int
    speed: int
    accuracy: int
    evasion: int
    critical: int
    critical_damage: int
    luck: int
    team: int

    def __init__(self, character: Character) -> None:
        self.character = character
        self.attributes = character.attributes
        self._skills = character.skills
        self._items = character.items

    # 动态生成属性访问器
    @staticmethod
    def _make_property(attr_name: str):
        @property
        def prop(self: CharacterAPI):
            return getattr(self.attributes, attr_name)
        return prop

    # 批量创建属性
    for attr in ['name', 'level', 'exp', 'max_hp', 'current_hp', 'max_mp',
                 'current_mp', 'attack', 'defense', 'magic_attack',
                 'magic_defense', 'speed', 'accuracy', 'evasion',
                 'critical', 'critical_damage', 'luck', 'team']:
        locals()[attr] = _make_property(attr)

    # 技能和物品的访问器
    @property
    def skills(self):
        """技能列表"""
        return self._skills

    @property
    def items(self):
        """物品列表"""
        return self._items

    # ----------------------------------------------------------------------------
    def examinevalid(self, attr: str):
        """
        检查并修正与属性关联的合法性：
        - 修改max_hp/max_mp时，确保current_hp/current_mp不超过新上限
        - 修改current_hp/current_mp时，确保在0~max之间
        """
        if attr == "max_hp":
            # 当血量上限降低时，当前血量不能超过新上限
            self.attributes.current_hp = min(
                self.attributes.current_hp,
                self.attributes.max_hp
            )
        elif attr == "max_mp":
            self.attributes.current_mp = min(
                self.attributes.current_mp,
                self.attributes.max_mp
            )
        elif attr == "current_hp":
            # 确保血量在0~max_hp之间，并同步存活状态
            self.attributes.current_hp = max(0, min(
                self.attributes.current_hp,
                self.attributes.max_hp
            ))

        elif attr == "current_mp":
            self.attributes.current_mp = max(0, min(
                self.attributes.current_mp,
                self.attributes.max_mp
            ))

    def change_attribute(self, attr: str, value: int):
        """
        修改角色的指定属性值，并根据属性类型检查和修正关联属性的合法性。

        Args:
            attr (str): 要修改的属性名称。
            value (int): 要增加到属性上的值，正数表示增加，负数表示减少。

        Raises:
            AttributeError: 如果指定的属性名称不存在于角色属性中。
        """
        if hasattr(self.attributes, attr):
            # 修改属性值
            new_value = getattr(self.attributes, attr) + value
            setattr(self.attributes, attr, new_value)
            # 检查并修正关联属性
            self.examinevalid(attr)
        else:
            raise AttributeError(f"角色没有属性 {attr}")

    def set_attribute(self, attr: str, value: int):
        """
        直接设置角色的指定属性值，并根据属性类型检查和修正关联属性的合法性。

        Args:
            attr (str): 要设置的属性名称。
            value (int): 要设置的属性值。

        Raises:
            AttributeError: 如果指定的属性名称不存在于角色属性中。
        """
        if hasattr(self.attributes, attr):
            # 直接设置属性值
            setattr(self.attributes, attr, value)
            # 检查并修正关联属性
            self.examinevalid(attr)
        else:
            raise AttributeError(f"角色没有属性 {attr}")
