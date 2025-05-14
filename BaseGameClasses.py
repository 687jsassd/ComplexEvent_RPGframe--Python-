#BaseGameClasses.py
#Author: assd687
#Version: 0.0.2a
#Description: Base classes of RPG.(Skills,Character,Items etc.)
#Date: 2025-05-14
from __future__ import annotations
from typing import List, TYPE_CHECKING,Any
from abc import ABC
from dataclasses import dataclass
import uuid
if TYPE_CHECKING:
    from Evframe import GameMessage,Handler  # 仅用于类型检查

#技能部分(待补充)
@dataclass
class BasicSkillAttributes:
    name:str
    description:str
    owner:'Character' #拥有者

class Skill(ABC):
    def __init__(self,attributes:BasicSkillAttributes):
        self.attributes=attributes
        self.uuid=uuid.uuid4()
        self.reg_type = f"SKILL_{self.__class__.__name__.upper()}"
        self._api=SkillAPI(self) #API接口
    
    def effect(self, msg: 'GameMessage') -> Any:
        """技能效果实现"""
        pass
    def reg(self,handler: 'Handler'):
        handler.register_type(self.reg_type, self.effect)
    @property
    def i(self):
        return self._api
    
class ActiveSkill(Skill):
    def __init__(self,attributes:BasicSkillAttributes):
        super().__init__(attributes)
        
    def effect(self, msg: 'GameMessage',*args:Any,**kwargs:Any) -> Any:
        """主动技能效果实现"""
        pass
    def trigger(self, msg: 'GameMessage', *args: Any, **kwargs: Any) -> Any:
        """触发技能效果"""
        return self.effect(msg, *args, **kwargs)

class PassiveSkill(Skill):
    def __init__(self,attributes:BasicSkillAttributes):
        super().__init__(attributes)
        
    def effect(self, msg: 'GameMessage') -> Any:
        """被动技能效果实现"""
        pass
    def update(self, msg: 'GameMessage') -> bool:
        """被动技能效果更新"""
        return self.effect(msg)
        

class SkillAPI:
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
        return self._name
    @property
    def description(self):
        return self._description
    @property
    def owner(self):
        return self._owner
    @property
    def uuid(self):
        return self._uuid
    @property
    def reg_type(self):
        return self._reg_type

#物品部分(待补充)
@dataclass
class BasicItemAttributes:
    name:str
    description:str

class Item(ABC):
    def __init__(self,attributes:BasicItemAttributes):
        self.attributes=attributes
        self._api=ItemAPI(self) #API接口

    @property
    def i(self):
        return self._api
    
class ItemAPI:
    def __init__(self, item: Item) -> None:
        self.item = item
        self.attributes = item.attributes
        self._name = item.attributes.name
        self._description = item.attributes.description
    
    @property
    def name(self):
        return self._name
    @property
    def description(self):
        return self._description

#角色部分
@dataclass
class BasicCharacterAttributes:
    name:str
    
    level:int=1 #等级 
    exp:int=0 #经验
    
    max_hp:int=100 #最大生命值
    current_hp:int=100 #当前生命值
    max_mp:int=100 #最大魔法值
    current_mp:int=100 #当前魔法值
    
    attack:int=10 #攻击力
    defense:int=10 #防御力
    magic_attack:int=10 #魔法攻击力
    magic_defense:int=10 #魔法防御力
    speed:int=10 #速度
    accuracy:int=100 #命中率
    evasion:int=5 #闪避率
    critical:int=5 #暴击率
    critical_damage:int=200 #暴击伤害
    luck:int=0 #幸运
    
    team:int=0 #队伍
    
    
class Character(ABC):
    def __init__(self,
                 attributes:BasicCharacterAttributes,
                 skills:List[Skill]=list(),
                 items:List[Item]=list(),):
        self.attributes=attributes
        self.skills:List[Skill]=list() or skills
        self.items:List[Item]=list() or items
        self._api=CharacterAPI(self) #API接口
        
    @property
    def i(self):
        return self._api
    
    def __str__(self):
        return f"{self.i.name}({self.i.team})"
    def __repr__(self):
        return f"{self.attributes},skills:{self.skills},items:{self.items},team:{self.i.team}"
        
class CharacterAPI:
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
    def _make_property(attr_name:str):
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
        return self._skills
        
    @property 
    def items(self):
        return self._items 
    
    #----------------------------------------------------------------------------
    def Examine_valid(self, attr: str):
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
        if hasattr(self.attributes, attr):
            # 修改属性值
            new_value = getattr(self.attributes, attr) + value
            setattr(self.attributes, attr, new_value)
            # 检查并修正关联属性
            self.Examine_valid(attr)
        else:
            raise AttributeError(f"角色没有属性 {attr}")

    def set_attribute(self, attr: str, value: int):
        if hasattr(self.attributes, attr):
            # 直接设置属性值
            setattr(self.attributes, attr, value)
            # 检查并修正关联属性
            self.Examine_valid(attr)
        else:
            raise AttributeError(f"角色没有属性 {attr}")
