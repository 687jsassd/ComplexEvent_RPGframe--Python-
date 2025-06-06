# pylint: skip-file
import unittest
import logging
import threading
import random
from typing import Any, List, Tuple  # type:ignore
from basegameclasses import (
    BasicCharacterAttributes,
    Character,
    BasicSkillAttributes,
    ActiveSkill,  # type:ignore
    PassiveSkill,
    BasicItemAttributes,  # type:ignore
    Item  # type:ignore
)
from evframe import (
    Handler,  # type:ignore
    GameMessage,
    MessageManager,
    EventResult,  # type:ignore
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
        if (msg.type == "DAMAGE" and msg.phase == MessagePhase.PRE
            and msg.receiver == self.attributes.owner
                and self.attributes.owner.i.current_hp > 0):
            print(f'{self.i.owner}荆棘护甲触发！反击30%伤害')
            # 计算反弹伤害
            dmg = msg.value(msg) if callable(msg.value) else msg.value
            reflect_dmg = int(dmg * self.reflect_percent / 100)
            if reflect_dmg > 0:
                # 创建反弹伤害消息
                reflect_msg = msg.create(
                    messagechain=msg.messagechain,
                    msg_type="DAMAGE",
                    sender=msg.receiver,
                    receiver=msg.sender,
                    value=reflect_dmg,
                    extra=[(MessageExtra.DAMAGE_TYPE, "反弹伤害")]
                )
                msg.messagechain.i.manager.acceptmsgp(reflect_msg)
                return True
        return False


class HealSkill(PassiveSkill):
    def __init__(self, attributes: BasicSkillAttributes):
        super().__init__(attributes)

    def effect(self, msg: 'GameMessage') -> Any:
        '''治疗效果：每当受到伤害后，回复1点HP'''
        if (msg.type == 'DAMAGE'
                and msg.phase == MessagePhase.POST
                and msg.receiver == self.i.owner
                and self.i.owner.i.current_hp > 0
                and msg.get_value() > 0):
            print(f'{self.i.owner}活力触发! 回复1HP')
            react_msg = msg.create(
                messagechain=msg.messagechain,
                msg_type='HEAL',
                sender=self.i.owner,
                receiver=self.i.owner,
                value=1,
            )
            msg.messagechain.i.manager.acceptmsg(react_msg)
            return True
        return False

# 定义技能A（攻击者增益[简单modifier测试]）


class SkillA(PassiveSkill):
    def effect(self, msg: GameMessage):
        if (msg.type == "DAMAGE" and msg.phase == MessagePhase.PRE and
                msg.sender == self.i.owner and msg.get_value() < 25):
            print(f"{self.i.owner.i.name} 触发技能A，伤害+10")
            msg.modify((ModifierType.SET_VALUE,
                        lambda x: x.get_value() + 10))
            return True
        return False

# 定义技能B（伤害减半反弹[自定义复杂MODIFIER测试]）


class SkillB(PassiveSkill):
    def effect(self, msg: GameMessage):
        if (msg.type == "DAMAGE" and msg.phase == MessagePhase.PRE and
                msg.receiver == self.i.owner and msg.get_value() > 10):
            def custom_modifier(msg: GameMessage, val: int) -> Tuple[Any, Any, bool]:
                raw_value = msg.get_value()
                reduced = msg.get_value() // 2
                reflect = msg.get_value() - reduced
                print(
                    f"{self.i.owner.i.name} 触发技能B，伤害减半为{reduced}，反弹{reflect}")
                msg.value = reduced
                # 创建反弹伤害
                reflect_msg = msg.create(
                    messagechain=msg.messagechain,
                    msg_type="DAMAGE",
                    sender=self.i.owner,
                    receiver=msg.sender,
                    value=reflect,
                    extra=[(MessageExtra.DAMAGE_TYPE, "反弹")]
                )
                msg.messagechain.i.manager.acceptmsgp(reflect_msg)
                # 别忘了解除注册
                msg.messagechain.manager.handler.unregister_modifier(
                    'SkillB_custom_modifier')
                return raw_value, reduced, True
            msg.messagechain.manager.handler.register_modifier(
                'SkillB_custom_modifier', custom_modifier)
            msg.modify(('SkillB_custom_modifier', 0))
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
                msg_type="HEAL",
                sender=self.i.owner,
                receiver=msg.receiver,
                value=2
            )
            msg.messagechain.i.manager.acceptmsg(heal_msg)
            return True
        return False

# 定义技能X


class SkillX(PassiveSkill):
    def effect(self, msg: GameMessage):
        if (msg.type == "DAMAGE"
            and msg.sender == self.i.owner
                and msg.phase == MessagePhase.PRE):
            print("触发技能X，增加5伤害(modifier)")
            msg.modify((ModifierType.SET_VALUE, 5+msg.get_value()))
            return True
        return False


class TestSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """初始化测试环境，只执行一次"""
        cls._lock = threading.Lock()  # 用于确保单线程执行
        random.seed(1)  # 新增：固定随机种子，消除随机因素干扰
        cls.manager = MessageManager()  # 初始化消息管理器和处理器
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

    # 测试例部分

    # 荆棘护甲测试->多连锁
    def test_thorn_armor_skill(self):
        """测试荆棘护甲技能"""
        print("\n\n\n=== 荆棘护甲：多连锁技能测试 ===")

        # 创建并注册荆棘护甲技能
        thorn_armor1 = ThornArmorSkill(
            BasicSkillAttributes(
                name="荆棘护甲", description="反弹30%伤害", owner=self.defender)
        )
        skill1 = HealSkill(
            BasicSkillAttributes(
                name="活力", description="每当受伤，回复1HP", owner=self.defender)
        )

        thorn_armor2 = ThornArmorSkill(
            BasicSkillAttributes(
                name="荆棘护甲", description="反弹30%伤害", owner=self.attacker)
        )
        skill2 = HealSkill(
            BasicSkillAttributes(
                name="活力", description="每当受伤，回复1HP", owner=self.attacker)
        )
        self.manager.register(thorn_armor1)
        self.manager.register(skill1)

        self.manager.register(thorn_armor2)
        self.manager.register(skill2)
        # 记录初始生命值
        attacker_initial_hp = self.attacker.i.current_hp
        defender_initial_hp = self.defender.i.current_hp
        print(attacker_initial_hp, defender_initial_hp)
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

    # 多技能响应测试->多响应
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

        # 注册技能到各角色
        skillA = SkillA(BasicSkillAttributes(
            name="技能A", owner=self.role1, description=''))
        skillB = SkillB(BasicSkillAttributes(
            name="技能B", owner=self.role2, description=''))
        skillC = SkillC(BasicSkillAttributes(
            name="技能C", owner=self.role3, description=''))
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

    # modifier测试->修饰器
    def test_modifiers(self):
        """测试修饰器功能"""
        print("\n\n\n=== 修饰器测试 ===")
        self.rop1 = Character(
            BasicCharacterAttributes(name="角色1.1", attack=20))
        self.rop2 = Character(
            BasicCharacterAttributes(name="角色2.1", defense=0))
        self.handler.register(self.rop1)
        self.handler.register(self.rop2)

        skillX = SkillX(BasicSkillAttributes(
            name="技能X", description='', owner=self.rop1))
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

    # 消息链变量测试->消息链
    def test_msgchainvar(self):
        """测试消息链变量在modifier中的调用"""
        print("\n\n\n=== modifier调用消息链变量测试 ===")
        # 使用 attacker, defender, visiter 角色,不再定义

        # 定义技能D
        # 1.自身攻击时(ATTACK-POST阶段)添加消息链变量testvar为随机1-3的值；
        # 2.伤害结算前(DAMAGE-PRE阶段)，每有一个testvar，伤害值*2(利用自定义modifier)
        # 例如testvar为3，攻击力为10，最终伤害应为10*2*2*2=80
        class SkillD(PassiveSkill):
            def effect(self, msg: GameMessage):
                # 效果1
                if (msg.type == "ATTACK"
                    and msg.sender == self.i.owner
                    and msg.phase == MessagePhase.PRE
                    and msg.sender
                        and msg.sender.i.current_hp > 0):

                    # 随机生成1-3的值
                    testvar = random.randint(1, 3)
                    # 添加到消息链变量(作用域签名为skillD)
                    msg.messagechain.i.vadd('skillD', 'testvar', testvar)

                    return True

                # 效果2
                elif (msg.type == "DAMAGE"
                      and msg.sender == self.i.owner
                      and msg.phase == MessagePhase.PRE
                      and msg.receiver
                      and msg.receiver.i.current_hp > 0):

                    # 自定义modifier函数(格式范例)
                    def custom_modifier(msg: GameMessage, val: Any) -> Tuple[Any, Any, bool]:
                        # 记录原值，声明修改后值
                        raw_value = msg.get_value()
                        modifiered_value = msg.get_value()

                        # 获取消息链变量(由于是消耗性变量，所以用vpop,不用vget)
                        testvar = msg.messagechain.i.vpop('skillD', 'testvar')
                        print(f"testvar值为{testvar}")

                        # 如果没有testvar，则不修改(但也是成功)
                        if testvar is None:
                            ret = (raw_value, modifiered_value, True)

                        # 如果有testvar，则每有一个则伤害*2
                        else:
                            for _ in range(testvar):
                                msg.value = msg.get_value() * 2
                            modifiered_value = msg.get_value()
                            print(
                                f"{self.i.owner.i.name} 触发技能D,伤害随机乘2,4或8,最终伤害{modifiered_value}")
                            ret = (raw_value, modifiered_value, True)

                        # 对于部分modifier,执行后立刻解除注册自身较好，防止状态污染。
                        msg.messagechain.manager.handler.unregister_modifier(
                            'SkillD_custom_modifier')

                        # 修改成功后，返回原值、修改后值、成功标志
                        return ret

                    # 注册自定义modifier
                    msg.messagechain.manager.handler.register_modifier(
                        'SkillD_custom_modifier', custom_modifier)
                    # 调用自定义modifier
                    msg.modify(('SkillD_custom_modifier', 0))
                    return True

                return False

        skillD = SkillD(BasicSkillAttributes(
            name="技能D", owner=self.attacker, description=''))
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

    # 治疗技能单独测试->基础治疗
    def test_heal_skill(self):
        """测试治疗技能（HealSkill）是否每次受伤后正确回复1HP"""
        print("\n\n\n=== 治疗技能单独测试 ===")

        # 创建测试角色（防御者装备治疗技能）
        test_defender = Character(BasicCharacterAttributes(
            name="治疗测试目标", max_hp=100, current_hp=100))
        heal_skill = HealSkill(BasicSkillAttributes(
            name="活力", owner=test_defender))
        self.manager.register(heal_skill)
        self.handler.register(test_defender)

        # 记录初始HP
        initial_hp = test_defender.i.current_hp

        # 发送3次伤害消息（每次10点伤害）
        for _ in range(3):
            damage_msg = GameMessage(
                messagechain=self.manager.messagechain,
                type="DAMAGE",
                sender=self.attacker,
                receiver=test_defender,
                value=10
            )
            self.manager.acceptmsg(damage_msg)
            self.manager.execte()

        # 预期HP：100 - (10*3) + (1*3) = 73
        expected_hp = initial_hp - 30 + 3
        self.assertEqual(test_defender.i.current_hp, expected_hp, "治疗技能回复量错误")
        print("✓ 治疗技能单独测试通过")

    # 队伍机制触发测试->同队/异队治疗
    def test_team_based_heal(self):
        """测试技能C是否仅在同队伍成员受伤时触发治疗"""
        print("\n\n\n=== 队伍机制触发测试 ===")

        # 创建不同队伍的角色（attacker默认team=0，visiter在setUp中team=1）
        # 注册技能C到visiter（队伍1）
        skillC = SkillC(BasicSkillAttributes(name="技能C", owner=self.visiter))
        self.manager.register(skillC)

        # 记录初始HP
        defender_initial_hp = self.defender.i.current_hp  # defender默认team=0（非visiter同队）
        visiter_initial_hp = self.visiter.i.current_hp    # visiter自己team=1（同队）

        # 攻击同队成员（visiter）
        damage_msg_team = GameMessage(
            messagechain=self.manager.messagechain,
            type="DAMAGE",
            sender=self.attacker,
            receiver=self.visiter,
            value=10
        )
        self.manager.acceptmsg(damage_msg_team)
        self.manager.execte()

        # 攻击异队成员（defender）
        damage_msg_other_team = GameMessage(
            messagechain=self.manager.messagechain,
            type="DAMAGE",
            sender=self.attacker,
            receiver=self.defender,
            value=10
        )
        self.manager.acceptmsg(damage_msg_other_team)
        self.manager.execte()

        # 验证：visiter应被治疗（+2），defender不应被治疗
        self.assertEqual(self.visiter.i.current_hp,
                         visiter_initial_hp - 10 + 2, "同队成员未触发治疗")
        self.assertEqual(self.defender.i.current_hp,
                         defender_initial_hp - 10, "异队成员错误触发治疗")
        print("✓ 队伍机制触发测试通过")

    # 消息阶段顺序测试->PRE/POST执行顺序
    def test_message_phase_order(self):
        """测试消息阶段（PRE/POST）是否按正确顺序触发技能"""
        print("\n\n\n=== 消息阶段顺序测试 ===")

        # 定义PRE阶段修改伤害的技能
        class PrePhaseSkill(PassiveSkill):
            def effect(self, msg: GameMessage):
                if msg.type == "DAMAGE" and msg.phase == MessagePhase.PRE:
                    # PRE阶段+5伤害
                    msg.modify((ModifierType.SET_VALUE, msg.get_value() + 5))
                    return True
                return False

        # 定义POST阶段治疗的技能
        class PostPhaseSkill(PassiveSkill):
            def effect(self, msg: GameMessage):
                if msg.type == "DAMAGE" and msg.phase == MessagePhase.POST:
                    # POST阶段治疗伤害值的10%
                    heal_value = int(msg.get_value() * 0.1)
                    heal_msg = msg.create(
                        messagechain=msg.messagechain,
                        msg_type="HEAL",
                        sender=msg.receiver,
                        receiver=msg.receiver,
                        value=heal_value
                    )
                    msg.messagechain.i.manager.acceptmsg(heal_msg)
                    return True
                return False

        # 注册技能到防御者
        pre_skill = PrePhaseSkill(BasicSkillAttributes(
            name="PRE阶段技能", owner=self.defender))
        post_skill = PostPhaseSkill(BasicSkillAttributes(
            name="POST阶段技能", owner=self.defender))
        self.manager.register(pre_skill)
        self.manager.register(post_skill)

        # 发送初始伤害消息（10点伤害）
        initial_damage = 10
        damage_msg = GameMessage(
            messagechain=self.manager.messagechain,
            type="DAMAGE",
            sender=self.attacker,
            receiver=self.defender,
            value=initial_damage
        )
        self.manager.acceptmsg(damage_msg)
        self.manager.execte()

        # 计算预期结果：
        # PRE阶段+5 → 实际伤害15
        # POST阶段治疗15*10%=1 → 最终HP变化：-15 +1 = -14
        expected_hp = self.defender.i.max_hp - 14
        self.assertEqual(self.defender.i.current_hp, expected_hp, "消息阶段执行顺序错误")
        print("✓ 消息阶段顺序测试通过")

    def test_multi_reflect_heal_chain(self):
        """测试多个角色同时装备荆棘护甲+治疗技能时的连锁反应"""
        print("\n\n\n=== 多角色反弹-治疗连锁测试 ===")

        # 为攻击者和防御者都装备荆棘护甲+治疗技能
        attacker_thorn = ThornArmorSkill(
            BasicSkillAttributes(name="荆棘甲", owner=self.attacker))
        attacker_heal = HealSkill(
            BasicSkillAttributes(name="活力", owner=self.attacker))
        defender_thorn = ThornArmorSkill(
            BasicSkillAttributes(name="荆棘甲", owner=self.defender))
        defender_heal = HealSkill(
            BasicSkillAttributes(name="活力", owner=self.defender))
        self.manager.register(attacker_thorn)
        self.manager.register(attacker_heal)
        self.manager.register(defender_thorn)
        self.manager.register(defender_heal)

        # 记录初始HP（假设最大HP均为100）
        initial_attacker_hp = self.attacker.i.current_hp  # 100
        initial_defender_hp = self.defender.i.current_hp  # 100

        # 攻击者发起40点伤害的攻击
        attack_msg = GameMessage(
            messagechain=self.manager.messagechain,
            type="ATTACK",
            sender=self.attacker,
            receiver=self.defender,
            value=40
        )
        self.manager.acceptmsg(attack_msg)
        self.manager.execte()

        # 计算预期流程：
        # 1. 防御者受到40点伤害（荆棘护甲触发，反弹30%即12点伤害给攻击者）
        # 2. 防御者治疗技能触发（POST阶段），回复1HP
        # 3. 攻击者受到12点反弹伤害（荆棘护甲触发，反弹30%即3.6→3点伤害给防御者）
        # 4. 攻击者治疗技能触发（POST阶段），回复1HP
        # 5. 防御者受到3点反弹伤害（荆棘护甲触发，反弹30%即0.9→0点伤害，无后续）
        # 最终HP计算：
        # 防御者：100 - 40（初始伤害） +1（治疗） -3（攻击者反弹） +1（治疗） = 59
        # 攻击者：100 -12（防御者反弹） +1（治疗） = 89
        self.assertEqual(self.defender.i.current_hp, 59, "防御者HP计算错误")
        self.assertEqual(self.attacker.i.current_hp, 89, "攻击者HP计算错误")
        print("✓ 多角色反弹-治疗连锁测试通过")

    # 测试例9：同队多成员受伤治疗验证
    def test_multi_teammate_heal(self):
        """测试技能C在多个同队成员受伤时的触发次数"""
        print("\n\n\n=== 同队多成员受伤治疗验证 ===")

        # 创建两个同队成员（team=1）
        teammate1 = Character(BasicCharacterAttributes(name="队友1", team=1))
        teammate2 = Character(BasicCharacterAttributes(name="队友2", team=1))
        self.handler.register(teammate1)
        self.handler.register(teammate2)

        # 注册技能C到visiter（team=1）
        skillC = SkillC(BasicSkillAttributes(name="技能C", owner=self.visiter))
        self.manager.register(skillC)

        # 记录初始HP
        t1_initial = teammate1.i.current_hp
        t2_initial = teammate2.i.current_hp

        # 同时攻击两个同队成员（各10点伤害）
        damage_msg1 = GameMessage(
            messagechain=self.manager.messagechain,
            type="DAMAGE",
            sender=self.attacker,
            receiver=teammate1,
            value=10
        )
        damage_msg2 = GameMessage(
            messagechain=self.manager.messagechain,
            type="DAMAGE",
            sender=self.attacker,
            receiver=teammate2,
            value=10
        )
        self.manager.acceptmsg(damage_msg1)
        self.manager.acceptmsg(damage_msg2)
        self.manager.execte()

        # 预期：每个受伤的同队成员触发一次技能C（各+2HP）
        self.assertEqual(teammate1.i.current_hp,
                         t1_initial - 10 + 2, "队友1未触发治疗")
        self.assertEqual(teammate2.i.current_hp,
                         t2_initial - 10 + 2, "队友2未触发治疗")
        print("✓ 同队多成员受伤治疗验证通过")

    # 测试例10：伤害增益与反弹技能叠加测试
    def test_buff_reflect_interaction(self):
        """测试SkillA（伤害增益）与SkillB（伤害反弹）的叠加效果"""
        print("\n\n\n=== 伤害增益与反弹技能叠加测试 ===")

        # 攻击者装备SkillA（伤害+10），防御者装备SkillB（伤害减半反弹）
        skillA = SkillA(BasicSkillAttributes(name="技能A", owner=self.attacker))
        skillB = SkillB(BasicSkillAttributes(name="技能B", owner=self.defender))
        self.manager.register(skillA)
        self.manager.register(skillB)

        # 记录初始HP（防御者max_hp=100）
        initial_defender_hp = self.defender.i.current_hp  # 100
        initial_attacker_hp = self.attacker.i.current_hp  # 100

        # 攻击者发起20点基础伤害的攻击
        attack_msg = GameMessage(
            messagechain=self.manager.messagechain,
            type="ATTACK",
            sender=self.attacker,
            receiver=self.defender,
            value=20
        )
        self.manager.acceptmsg(attack_msg)
        self.manager.execte()

        # 计算预期流程：
        # 1. SkillA触发（PRE阶段）：伤害+10 → 总伤害30
        # 2. SkillB触发（PRE阶段）：伤害减半为15，反弹15点伤害给攻击者
        # 3. 防御者最终受到15点伤害，攻击者受到15点反弹伤害
        self.assertEqual(self.defender.i.current_hp, 100 - 15, "防御者伤害计算错误")
        self.assertEqual(self.attacker.i.current_hp, 100 - 15, "攻击者反弹伤害计算错误")
        print("✓ 伤害增益与反弹技能叠加测试通过")

    # 复杂测试例11：无限反弹测试
    def test_infinite_reflect(self):
        """测试SkillB（伤害反弹）是否能无限反弹"""
        print("\n\n\n=== 无限反弹测试 ===")
        # 攻击者和防御者均有伤害反弹技能。

        class SkillY(PassiveSkill):
            def effect(self, msg: GameMessage):
                if (msg.type == "DAMAGE"
                    and msg.phase == MessagePhase.POST
                    and msg.receiver and msg.sender
                        and msg.receiver == self.i.owner
                        and msg.sender != self.i.owner
                        and msg.receiver.i.current_hp > 0):
                    reflect_msg = msg.create(
                        messagechain=msg.messagechain,
                        msg_type="DAMAGE",
                        sender=msg.receiver,
                        receiver=msg.sender,
                        value=msg.get_value()  # 反弹剩余伤害
                    )
                    msg.messagechain.i.manager.acceptmsg(reflect_msg)
                    return True
                return False

        # 注册技能到attacker和defender
        skillY1 = SkillY(BasicSkillAttributes(name="技能Y", owner=self.attacker))
        skillY2 = SkillY(BasicSkillAttributes(name="技能Y", owner=self.defender))
        self.manager.register(skillY1)
        self.manager.register(skillY2)

        # 修改攻击者和防御者HP
        self.attacker.i.set_attribute('max_hp', 1000000)
        self.attacker.i.set_attribute('current_hp', 1000000)
        self.defender.i.set_attribute('max_hp', 1000000)
        self.defender.i.set_attribute('current_hp', 1000000)

        # 攻击者发起11点基础伤害的攻击
        attack_msg = GameMessage(
            messagechain=self.manager.messagechain,
            type="ATTACK",
            sender=self.attacker,
            receiver=self.defender,
            value=11
        )
        self.manager.acceptmsg(attack_msg)

        self.manager.set_stopnum(4000)  # 这里把单消息队列长度设置为4000，这个长度很长，可以代表无限循环。
        # 预期是无限循环，所以会遇到长消息终止，这时会有ValueError，出现则代表通过
        try:
            with self.assertRaisesRegex(
                ValueError,
                r"^长消息错误:单消息队列过长，已停止执行$"  # 正则匹配完整消息
            ):
                self.manager.execte()  # 触发可能抛出异常的操作
        except AssertionError as e:
            # 捕获断言失败（未抛出异常或消息不匹配）
            self.fail(f"无限反弹测试失败: {str(e)}")
        else:
            # 未触发异常时（已通过断言）
            print("✓ 无限反弹测试通过")


if __name__ == "__main__":
    # 在程序入口处添加
    logging.basicConfig(
        level=logging.INFO,  # 设置日志级别
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('game.log'),  # 输出到文件
            # logging.StreamHandler()  # 输出到控制台
        ]
    )
    unittest.main(verbosity=2)
