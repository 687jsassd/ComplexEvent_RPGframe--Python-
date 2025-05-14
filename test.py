import unittest,logging
from typing import Any,List,Tuple  #type:ignore
from BaseGameClasses import (
    BasicCharacterAttributes,
    Character,
    BasicSkillAttributes,
    ActiveSkill,#type:ignore
    PassiveSkill,
    BasicItemAttributes,#type:ignore
    Item#type:ignore
)
from Evframe import (
    Handler,#type:ignore
    GameMessage,
    MessageManager,
    EventResult,#type:ignore
    MessagePhase,
    MessageExtra
)

class ThornArmorSkill(PassiveSkill):
    def __init__(self, attributes: BasicSkillAttributes):
        super().__init__(attributes)
        self.reflect_percent = 30  # 反弹30%伤害
        
    def effect(self, msg: 'GameMessage') -> Any:
        """荆棘护甲效果：反弹30%伤害"""
        if (msg.type == "DAMAGE" and msg.phase==MessagePhase.PRE 
        and msg.receiver == self.attributes.owner 
        and self.attributes.owner.i.current_hp>0
        and msg.get_extra(MessageExtra.DAMAGE_TYPE)!='反弹伤害'):
            print(f'{self.i.owner}荆棘护甲触发！反击30%伤害')
            # 计算反弹伤害
            dmg=msg.value(msg) if callable(msg.value) else msg.value
            reflect_dmg = int(dmg * self.reflect_percent / 100)
            if reflect_dmg > 0:
                # 创建反弹伤害消息
                reflect_msg = msg.create(
                    messagechain=msg.messagechain,
                    type="DAMAGE",
                    sender=msg.receiver,
                    receiver=msg.sender,
                    value=reflect_dmg,
                    extra=[(MessageExtra.DAMAGE_TYPE, "反弹伤害")]
                )
                msg.messagechain.i.manager.acceptmsgp(reflect_msg)
                return True
        return False

class HealSkill(PassiveSkill):
    def __init__(self,attributes:BasicSkillAttributes):
        super().__init__(attributes)
    def effect(self,msg:'GameMessage') -> Any:
        '''治疗效果：每当受到伤害后，回复1点HP'''
        if (msg.type == 'DAMAGE' 
        	and msg.phase==MessagePhase.POST
        	and msg.receiver == self.i.owner
        	and self.i.owner.i.current_hp>0
        	and msg.get_value()>0):
            print(f'{self.i.owner}活力触发! 回复1HP')
            react_msg=msg.create(
            		messagechain=msg.messagechain,
            		type='HEAL',
            		sender=self.i.owner,
            		receiver=self.i.owner,
            		value=1,
            	)
            msg.messagechain.i.manager.acceptmsg(react_msg)
            return True
        return False
            	

class TestSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """初始化测试环境，只执行一次"""
        cls.manager = MessageManager()
        cls.handler = cls.manager.handler
    
    def setUp(self):
        """每个测试用例执行前都会调用"""
        # 为每个测试创建独立的角色实例
        self.attacker = Character(BasicCharacterAttributes(name="战士", attack=20))
        self.defender = Character(BasicCharacterAttributes(name="法师", defense=0))
        
        # 注册角色
        self.handler.register(self.attacker)
        self.handler.register(self.defender)

    def tearDown(self):
        """每个测试用例执行后都会调用"""
        # 清理注册的角色
        self.handler.unregister(self.attacker)
        self.handler.unregister(self.defender)


    def test_thorn_armor_skill(self):
        """测试荆棘护甲技能"""
        print("\n=== 被动技能测试 ===")
        
        # 创建并注册荆棘护甲技能
        thorn_armor1 = ThornArmorSkill(
            BasicSkillAttributes(name="荆棘护甲", description="反弹30%伤害", owner=self.defender)
        )
        skill1 = HealSkill(
            BasicSkillAttributes(name="活力", description="每当受伤，回复1HP", owner=self.defender)
        )
        
        thorn_armor2 = ThornArmorSkill(
            BasicSkillAttributes(name="荆棘护甲", description="反弹30%伤害", owner=self.attacker)
        )
        skill2 = HealSkill(
            BasicSkillAttributes(name="活力", description="每当受伤，回复1HP", owner=self.attacker)
        )
        self.manager.register(thorn_armor1)
        self.manager.register(skill1)

        self.manager.register(thorn_armor2)
        self.manager.register(skill2)
        # 记录初始生命值
        attacker_initial_hp = self.attacker.i.current_hp
        defender_initial_hp = self.defender.i.current_hp
        print(attacker_initial_hp,defender_initial_hp)
        # 发送伤害消息(20点伤害)
        damage_msg = GameMessage(
            messagechain=self.manager.messagechain,
            type="ATTACK",
            value=20,
            sender=self.attacker,
            receiver=self.defender
        )
        self.manager.acceptmsg(damage_msg)
        self.manager.execte()
        
        # 验证伤害效果
        expected_defender_hp = defender_initial_hp - 19  # 20 -1=19
        expected_attacker_hp = attacker_initial_hp - 5   # 20*0.3=6 6-1=5
        
        self.assertEqual(self.defender.i.current_hp, expected_defender_hp)
        self.assertEqual(self.attacker.i.current_hp, expected_attacker_hp)
        print("✓ 荆棘护甲与活力技能测试通过")
        #卸载技能
        self.manager.unregister(thorn_armor1)
        self.manager.unregister(skill1)
        self.manager.unregister(thorn_armor2)
        self.manager.unregister(skill2)
        print("✓ 技能卸载成功")
        print("="*50)

    def test_complex_skills_interaction(self):
        """测试多个被动技能的复杂交互"""
        print("\n=== 复杂被动技能交互测试 ===")
        
        # 创建角色（默认team=0）
        self.role1 = Character(BasicCharacterAttributes(name="角色1", attack=20))
        self.role2 = Character(BasicCharacterAttributes(name="角色2", defense=0))
        self.role3 = Character(BasicCharacterAttributes(name="角色3"))
        
        # 注册角色到处理器
        self.handler.register(self.role1)
        self.handler.register(self.role2)
        self.handler.register(self.role3)

        # 定义技能A（攻击者增益[简单modifier测试]）
        class SkillA(PassiveSkill):
            def effect(self, msg: GameMessage):
                print("接收到消息，进行检查:",
                      (msg.type == 'DAMAGE'),
                      (msg.phase == MessagePhase.PRE),
                      (msg.sender == self.i.owner),
                      (msg.get_value() < 25))
                if (msg.type == "DAMAGE" and msg.phase == MessagePhase.PRE and 
                    msg.sender == self.i.owner and msg.get_value() < 25):
                    print(f"{self.i.owner.i.name} 触发技能A，伤害+10")
                    msg.modify(('set_value',lambda x:x.get_value() + 10))
                    return True
                return False
        
        # 定义技能B（伤害减半反弹[自定义复杂MODIFIER测试]）
        class SkillB(PassiveSkill):
            def effect(self, msg: GameMessage):
                if (msg.type == "DAMAGE" and msg.phase == MessagePhase.PRE and 
                    msg.receiver == self.i.owner and msg.get_value() > 10):
                    def custom_modifier(msg: GameMessage,val:int) -> Tuple[Any,Any,bool]:
                        raw_value=msg.get_value()
                        reduced = msg.get_value() // 2
                        reflect = msg.get_value() - reduced
                        print(f"{self.i.owner.i.name} 触发技能B，伤害减半为{reduced}，反弹{reflect}")
                        msg.value = reduced
                        # 创建反弹伤害
                        reflect_msg = msg.create(
                            messagechain=msg.messagechain,
                            type="DAMAGE",
                            sender=self.i.owner,
                            receiver=msg.sender,
                            value=reflect,
                            extra=[(MessageExtra.DAMAGE_TYPE, "反弹")]
                        )
                        msg.messagechain.i.manager.acceptmsgp(reflect_msg)
                        #别忘了解除注册
                        msg.messagechain.manager.handler.unregister_modifier('SkillB_custom_modifier')
                        return raw_value,reduced,True
                    msg.messagechain.manager.handler.register_modifier('SkillB_custom_modifier',custom_modifier)
                    msg.modify(('SkillB_custom_modifier',0))
                    return True
                return False
        # 定义技能C（队友治疗[不使用modifier]）
        class SkillC(PassiveSkill):
            def effect(self, msg: GameMessage):
                if (msg.type == "DAMAGE"
                    and msg.phase == MessagePhase.POST
                    and msg.receiver 
                    and msg.receiver.i.team == self.i.owner.i.team):
                    print(f"{self.i.owner.i.name} 触发技能C，治疗{msg.receiver.i.name}")
                    heal_msg = msg.create(
                        messagechain=msg.messagechain,
                        type="HEAL",
                        sender=self.i.owner,
                        receiver=msg.receiver,
                        value=2
                    )
                    msg.messagechain.i.manager.acceptmsg(heal_msg)
                    return True
                return False
        
        # 注册技能到各角色
        skillA = SkillA(BasicSkillAttributes(name="技能A", owner=self.role1,description=''))
        skillB = SkillB(BasicSkillAttributes(name="技能B", owner=self.role2,description=''))
        skillC = SkillC(BasicSkillAttributes(name="技能C", owner=self.role3,description=''))
        self.manager.register(skillA)
        self.manager.register(skillB)
        self.manager.register(skillC)

        # 记录初始生命值
        initial_hp = {
            'role1': self.role1.i.current_hp,
            'role2': self.role2.i.current_hp,
            'role3': self.role3.i.current_hp
        }

        # 角色1发起攻击（原始伤害20）
        attack_msg = GameMessage(
            messagechain=self.manager.messagechain,
            type="ATTACK",
            sender=self.role1,
            receiver=self.role2,
            value=20
        )
        self.manager.acceptmsg(attack_msg)
        self.manager.execte()  # 执行消息处理

        # 验证结果
        expected_hp_role2 = initial_hp['role2'] - 13  # (20+10)/2=15伤害，治疗后+2
        expected_hp_role1 = initial_hp['role1'] - 13  # 反弹15伤害，治疗后+2
        self.assertEqual(self.role2.i.current_hp, expected_hp_role2, 
                        "角色2生命值计算错误")
        self.assertEqual(self.role1.i.current_hp, expected_hp_role1,
                        "角色1生命值计算错误")
        self.assertEqual(self.role3.i.current_hp, initial_hp['role3'],
                        "角色3生命值不应变化")
        print("✓ 复杂技能交互测试通过")
        
        #卸载技能
        self.manager.unregister(skillA)
        self.manager.unregister(skillB)
        self.manager.unregister(skillC)
        self.handler.unregister(self.role1)
        self.handler.unregister(self.role2)
        self.handler.unregister(self.role3)

    def test_modifiers(self):
        """测试修饰器功能"""
        print("\n=== 修饰器测试 ===")
        self.rop1 = Character(BasicCharacterAttributes(name="角色1.1", attack=20))
        self.rop2 = Character(BasicCharacterAttributes(name="角色2.1", defense=0))
        self.handler.register(self.rop1)
        self.handler.register(self.rop2)

        # 定义技能
        class SkillX(PassiveSkill):
            def effect(self, msg: GameMessage):
                if (msg.type == "DAMAGE" 
                    and msg.sender == self.i.owner
                    and msg.phase==MessagePhase.PRE):
                    print("触发技能X，增加5伤害(modifier)")
                    msg.modify(('set_value',5+msg.get_value()))
                    return True
                return False

        skillX = SkillX(BasicSkillAttributes(name="技能X", description='',owner=self.rop1))
        self.manager.register(skillX)
        # 发送攻击消息
        attack_msg = GameMessage(
            messagechain=self.manager.messagechain,
            type="ATTACK",
            sender=self.rop1,
            receiver=self.rop2,
            value=20
        )
        
        self.manager.acceptmsg(attack_msg)
        self.manager.execte()
        
        self.assertEqual(self.rop2.i.current_hp, self.rop2.i.max_hp - 25,
                        "角色2生命值计算错误")
        
        print("✓ 修饰器测试通过")
        #卸载技能
        self.manager.unregister(skillX)
        self.handler.unregister(self.rop1)
        self.handler.unregister(self.rop2)

if __name__ == "__main__":
    # 在程序入口处添加
    logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game.log'),  # 输出到文件
        logging.StreamHandler()  # 输出到控制台
    ]
)
    unittest.main(verbosity=2)
    