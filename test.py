import unittest,logging,threading,random
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
    MessageExtra,
    ModifierType
)

# 定义颜色ANSI转义码（终端显示用）
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RESET = "\033[0m"

class ThornArmorSkill(PassiveSkill):
    def __init__(self, attributes: BasicSkillAttributes):
        super().__init__(attributes)
        self.reflect_percent = 30  # 反弹30%伤害
        
    def effect(self, msg: 'GameMessage') -> Any:
        """荆棘护甲效果：反弹30%伤害"""
        if (msg.type == "DAMAGE" and msg.phase==MessagePhase.PRE 
        and msg.receiver == self.attributes.owner 
        and self.attributes.owner.i.current_hp>0):
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
        cls._lock = threading.Lock()  # 用于确保单线程执行
        random.seed(1)  # 新增：固定随机种子，消除随机因素干扰
        cls.manager = MessageManager() # 初始化消息管理器和处理器
        cls.handler = cls.manager.handler
        logging.basicConfig(level=logging.INFO)
    
    def setUp(self):
        """每个测试用例执行前都会调用"""
        with self._lock:
            
            # 为每个测试创建独立的角色实例（带颜色标识）
            self.attacker = Character(BasicCharacterAttributes(
                name=f"{RED}战士{RESET}",  # 红色标识
                attack=20
            ))
            
            self.defender = Character(BasicCharacterAttributes(
                name=f"{GREEN}法师{RESET}",  # 绿色标识
                defense=0
            ))
            
            self.visiter = Character(BasicCharacterAttributes(  
                name=f"{YELLOW}访客{RESET}",  # 黄色标识
                attack=0,  # 默认无攻击
                defense=0,   # 默认无防御
                max_hp=1000,  # 高生命值
                current_hp=1000,
                team=1  # 设为非0队伍，用于区分  
            ))
            
            # 注册角色
            self.handler.register(self.attacker)
            self.handler.register(self.defender)
            self.handler.register(self.visiter)
    
    def tearDown(self):
        """每个测试用例执行后都会调用"""
        with self._lock:
            # 重置消息管理器
            self.manager.reset()

    #测试例部分
    
    #荆棘护甲测试->多连锁
    def test_thorn_armor_skill(self):
        """测试荆棘护甲技能"""
        print("\n\n\n=== 荆棘护甲：多连锁技能测试 ===")
        
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
        # 发送伤害消息(82点伤害)
        damage_msg = GameMessage(
            messagechain=self.manager.messagechain,
            type="ATTACK",
            value=82,
            sender=self.attacker,
            receiver=self.defender
        )
        self.manager.acceptmsg(damage_msg)
        self.manager.execte()
        
        # 验证伤害效果
        expected_defender_hp = defender_initial_hp - 87  
        expected_attacker_hp = attacker_initial_hp - 24   
        
        self.assertEqual(self.defender.i.current_hp, expected_defender_hp)
        self.assertEqual(self.attacker.i.current_hp, expected_attacker_hp)
        print("✓ 荆棘护甲与活力技能测试通过")
        
    #多技能响应测试->多响应
    def test_complex_skills_interaction(self):
        """测试多个被动技能的复杂交互"""
        print("\n\n\n=== 复杂被动技能交互测试 ===")
        
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
                if (msg.type == "DAMAGE" and msg.phase == MessagePhase.PRE and 
                    msg.sender == self.i.owner and msg.get_value() < 25):
                    print(f"{self.i.owner.i.name} 触发技能A，伤害+10")
                    msg.modify((ModifierType.SET_VALUE,lambda x:x.get_value() + 10))
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
        
    #modifier测试->修饰器
    def test_modifiers(self):
        """测试修饰器功能"""
        print("\n\n\n=== 修饰器测试 ===")
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
                    msg.modify((ModifierType.SET_VALUE,5+msg.get_value()))
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

    #消息链变量测试->消息链
    def test_msgchainvar(self):
        """测试消息链变量在modifier中的调用"""
        print("\n\n\n=== modifier调用消息链变量测试 ===")
        #使用 attacker, defender, visiter 角色,不再定义
        
        # 定义技能D
        # 1.自身攻击时(ATTACK-POST阶段)添加消息链变量testvar为随机1-3的值；
        # 2.伤害结算前(DAMAGE-PRE阶段)，每有一个testvar，伤害值*2(利用自定义modifier)
        # 例如testvar为3，攻击力为10，最终伤害应为10*2*2*2=80
        class SkillD(PassiveSkill):
            def effect(self, msg: GameMessage):
                #效果1
                if (msg.type == "ATTACK"
                    and msg.sender == self.i.owner
                    and msg.phase==MessagePhase.PRE
                    and msg.sender
                    and msg.sender.i.current_hp>0):
                    
                    #随机生成1-3的值
                    testvar = random.randint(1, 3)
                    #添加到消息链变量(作用域签名为skillD)
                    msg.messagechain.i.vadd('skillD','testvar',testvar)
                    
                    return True
                
                #效果2
                elif (msg.type == "DAMAGE"
                    and msg.sender == self.i.owner
                    and msg.phase==MessagePhase.PRE
                    and msg.receiver 
                    and msg.receiver.i.current_hp>0):
                    
                    #自定义modifier函数(格式范例)
                    def custom_modifier(msg: GameMessage,val:Any) -> Tuple[Any,Any,bool]:
                        #记录原值，声明修改后值
                        raw_value=msg.get_value()
                        modifiered_value=msg.get_value()
                        
                        #获取消息链变量(由于是消耗性变量，所以用vpop,不用vget)
                        testvar = msg.messagechain.i.vpop('skillD','testvar')
                        print(f"testvar值为{testvar}")
                        
                        #如果没有testvar，则不修改(但也是成功)
                        if testvar is None:
                            ret=(raw_value,modifiered_value,True)
                        
                        #如果有testvar，则每有一个则伤害*2
                        else:
                            for _ in range(testvar):
                                msg.value = msg.get_value() * 2
                            modifiered_value = msg.get_value()
                            print(f"{self.i.owner.i.name} 触发技能D,伤害随机乘2,4或8,最终伤害{modifiered_value}")
                            ret=(raw_value,modifiered_value,True)

                        #对于部分modifier,执行后立刻解除注册自身较好，防止状态污染。
                        msg.messagechain.manager.handler.unregister_modifier('SkillD_custom_modifier')
                        
                        #修改成功后，返回原值、修改后值、成功标志
                        return ret
                            
                    #注册自定义modifier
                    msg.messagechain.manager.handler.register_modifier('SkillD_custom_modifier',custom_modifier)
                    #调用自定义modifier
                    msg.modify(('SkillD_custom_modifier',0))
                    return True
                
                return False
                    
        skillD = SkillD(BasicSkillAttributes(name="技能D", owner=self.attacker,description=''))
        self.manager.register(skillD)

        # 发送攻击消息
        attack_msg = GameMessage(
            messagechain=self.manager.messagechain,
            type="ATTACK",
            sender=self.attacker,
            receiver=self.defender,
            value=10 
        )
        self.manager.acceptmsg(attack_msg)
        self.manager.execte()
        print("✓ 消息链变量测试通过")
                    

if __name__ == "__main__":
    # 在程序入口处添加
    logging.basicConfig(
    level=logging.INFO,  # 设置日志级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('game.log'),  # 输出到文件
        #logging.StreamHandler()  # 输出到控制台
    ]
)
    unittest.main(verbosity=2)
    