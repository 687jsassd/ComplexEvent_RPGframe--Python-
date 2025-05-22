#Evframe.py
#Author: assd687
#Version: 0.0.11a
#Description: A simple RPG event trigger frame.
#Date: 2025-05-22

from typing import Optional,List,Dict,Tuple,Deque,Set,Callable,Any,Protocol,Union,DefaultDict
from dataclasses import dataclass
from enum import Enum,auto
from collections import deque,defaultdict
import uuid,random,copy,logging
import BaseGameClasses as bgc

logger=logging.getLogger(__name__)
logger.setLevel(logging.INFO)
#事件处理器的返回值的枚举
class EventResult(Enum):
    CONTINUE = auto() #继续执行
    STOP = auto() #停止执行
    SKIP = auto() #跳过该事件
    RE_INPUT = auto() #重新输入
#消息处理阶段的枚举
class MessagePhase(Enum):
    PRE = 0  #预处理(值0)
    MAIN = 1  #主处理(值1)
    POST = 2  #后处理(值2)
    NONE = 3  #无(这类消息，事件管理器会自动拆分为PRE,MAIN和POST,值3)
#作为Message中extra的一些可用关键字
class MessageExtra(Enum):
    #消息处理过程相关
    IGNORE = ("ignore", bool)   # (是否忽略该消息, 必须为布尔值)
    #消息加工过程相关
    MODIFY_TYPE = ("modify_type", str)    # (修改的消息类型, 必须为字符串)
    MODIFY_VALUE = ("modify_value", Any)  # (修改的值, 可以是任意类型)
    RAW_VALUE = ("raw_value", Any)        # (原始值, 可以是任意类型)
    
    #战斗相关
    RAW_DAMAGE = ("raw_damage", int)        # (原始伤害值, 必须为整数)
    AFTER_CRIT_DAMAGE = ("after_crit_damage", int)  # (暴击后伤害值, 必须为整数)
    CRIT = ("crit", bool)                  # (是否暴击, 必须为布尔值)
    DODGE = ("dodge", bool)               # (是否闪避, 必须为布尔值)
    DAMAGE_TYPE = ("damage_type", str)     # (伤害类型, 必须为字符串)
    
    @property
    def key(self):
        return self.value[0]
    
    @property 
    def expected_type(self):
        return self.value[1]

#作为内置MODIFY_TYPE的枚举(用于消息加工)
class ModifierType(Enum):
    SET_VALUE = auto() #对数值的修改
    SET_SENDER = auto() #设置发送者
    SET_RECEIVER = auto() #设置接受者
    UPDATE_EXTRA = auto() #更新extra中的值
    REMOVE_EXTRA = auto() #移除extra中的值
    REMOVE_MODIFIER = auto() #移除一个Modifier
    
    

#中心事件处理器，统一处理基本事件如受伤，加血。
#角色和技能应该由这个处理器注册和统一管理。处理的对象仅限于已经被注册的对象(后期修改)。
class Handler:
    # 定义无操作的占位函数并添加类型注解
    def __init__(self,father:Optional['Handler'] =None):
        #允许继承父管理器的值
        if father:
            self.chars=father.chars
            self.skills=father.skills
            self.items=father.items
            self._registered_chars=father._registered_chars
            self._registered_skills=father._registered_skills
            self._registered_items=father._registered_items
            self._registered_types=father._registered_types
            self._registered_modifiers=father._registered_modifiers
            self.ev_handlers=father.ev_handlers 
            self._pre_handlers=father._pre_handlers 
            self._post_handlers=father._post_handlers 
            self._custom_modifiers=father._custom_modifiers
        else:    
            self.chars:Set[bgc.Character]=set()
            self.skills:Set[bgc.Skill]=set()
            self.items:Set[bgc.Item]=set()
            self._registered_chars:Set[bgc.Character]=set()
            self._registered_skills:Set[bgc.Skill]=set()
            self._registered_items:Set[bgc.Item]=set()
            self._registered_types:Set[str]=set()
            self._registered_modifiers:Set[str]=set()
            self.ev_handlers:Dict[str,Callable[['GameMessage'],Any]] = {}  # 主处理函数
            self._pre_handlers:Dict[str,Callable[['GameMessage'],Any]] = {}  # 预处理函数
            self._post_handlers:Dict[str,Callable[['GameMessage'],Any]] = {}  # 后处理函数
            self._custom_modifiers:Dict[str,Callable[['GameMessage',Any],Tuple[Any,Any,bool]]] = {}
    def _noop_handler(self,msg:'GameMessage')->Tuple[int, EventResult, str]:
        return (0, EventResult.CONTINUE, "无操作")
    
    def register(self,obj:Union[bgc.Character,bgc.Skill,bgc.Item]):
        '''
           注册角色，技能或物品
        '''
        if isinstance(obj,bgc.Character):
            self.chars.add(obj)
            self._registered_chars.add(obj)
        elif isinstance(obj,bgc.Skill):
            self.skills.add(obj)
            self._registered_skills.add(obj)
        elif isinstance(obj,bgc.Item): #type:ignore
            self.items.add(obj)
            self._registered_items.add(obj)
        else:
            raise ValueError('只能注册角色，技能或物品')
        
        if (hasattr(obj, 'reg_type') and 
            hasattr(obj, 'reg') and 
            callable(obj.reg) and  #type:ignore
            not self.is_reg(obj.reg_type)): #type:ignore
            obj.reg(self) #type:ignore
    
    def unregister(self,obj:Union[bgc.Character,bgc.Skill,bgc.Item]):
        '''
           注销角色，技能或物品
        '''
        if isinstance(obj,bgc.Character):
            self.chars.remove(obj)
            self._registered_chars.remove(obj)
        elif isinstance(obj,bgc.Skill):
            self.skills.remove(obj)
            self._registered_skills.remove(obj)
        elif isinstance(obj,bgc.Item): #type:ignore
            self.items.remove(obj)
            self._registered_items.remove(obj)
        else:
            raise ValueError('只能注销角色，技能或物品')        
    
    def register_type(self, msg_type: str, handler: Callable[['GameMessage'], Any], 
                     phase: MessagePhase = MessagePhase.MAIN):
        '''
           注册新事件类型并绑定其函数
            
           参数：
           msg_type: 事件类型
           handler: 事件函数
           phase: 处理阶段 (默认为MAIN)
        '''
        
        if phase != MessagePhase.MAIN and not self.is_reg(msg_type):
            raise ValueError('必须先注册MAIN阶段处理函数才能注册PRE/POST阶段')
            
        if msg_type not in self._registered_types:
            # 新注册时初始化所有阶段的处理函数
            self._pre_handlers[msg_type] = self._noop_handler
            self.ev_handlers[msg_type] = self._noop_handler
            self._post_handlers[msg_type] = self._noop_handler
            self._registered_types.add(msg_type)
            
        if phase == MessagePhase.PRE:
            self.replace_type(msg_type, handler, MessagePhase.PRE)
        elif phase == MessagePhase.MAIN:
            self.replace_type(msg_type, handler, MessagePhase.MAIN)
        elif phase == MessagePhase.POST:
            self.replace_type(msg_type, handler, MessagePhase.POST)
            
        logger.info(f'已经注册{msg_type}的{phase.name}阶段处理器')

    def replace_type(self, msg_type: str, handler: Callable[['GameMessage'], Any], 
                    phase: MessagePhase = MessagePhase.MAIN):
        '''
           替换已注册事件的处理函数
            
           参数：
           msg_type: 事件类型
           handler: 新处理函数
           phase: 处理阶段 (默认为MAIN)
        '''
        if not self.is_reg(msg_type):
            raise ValueError('事件类型未注册,不能替换')
            
        if phase == MessagePhase.PRE:
            self._pre_handlers[msg_type] = handler
        elif phase == MessagePhase.MAIN:
            self.ev_handlers[msg_type] = handler
        elif phase == MessagePhase.POST:
            self._post_handlers[msg_type] = handler
            
        logger.info(f'已经替换{msg_type}的{phase.name}阶段处理器')

    def unregister_type(self, msg_type: str):
        '''
           移除已经注册的事件及其所有阶段的函数
        '''
        if msg_type in self._registered_types:
            self._registered_types.remove(msg_type)
            del self._pre_handlers[msg_type]
            del self.ev_handlers[msg_type]
            del self._post_handlers[msg_type]
            logger.info(f'已经移除{msg_type}的所有阶段处理器')
        else:
            raise ValueError('事件类型未注册,不能删除')

        self.custom_modifiers = {}
        
    def register_modifier(self, modifier_type: str, handler: Callable[['GameMessage', Any], Tuple[Any, Any, bool]]):
        """注册自定义modifier处理器"""
        self._custom_modifiers[modifier_type] = handler
        self._registered_modifiers.add(modifier_type)
        logger.info(f"注册自定义modifier: {modifier_type}")
        
    def unregister_modifier(self, modifier_type: str):
        """注销自定义modifier处理器""" 
        if modifier_type in self._custom_modifiers:
            del self._custom_modifiers[modifier_type]
            self._registered_modifiers.remove(modifier_type)
      
    def handles(self, msg_type: str, phase: MessagePhase = MessagePhase.MAIN) -> Callable[[Callable[['GameMessage'], Any]], Callable[['GameMessage'], Any]]:
        '''
           装饰器模式注册事件
           区别于直接调用register_type,该方法提供了采用装饰器模式直接在定义函数时绑定其消息类型的方案。
           
           参数：
           msg_type: 事件类型
           phase: 处理阶段 (默认为MAIN)
           
           使用示例：
           @xxx.handles('poison', MessagePhase.PRE)  # 注册预处理函数
           def poison_pre(xxx):
               pass
               
           @xxx.handles('poison')  # 默认注册主处理函数
           def poison_main(xxx):
               pass
        '''
        def decorator(func: Callable[['GameMessage'], Any]) -> Callable[['GameMessage'], Any]:
            self.register_type(msg_type, func, phase)
            return func
        return decorator
    
    def is_reg(self,objc:Union[bgc.Character,bgc.Skill,bgc.Item,str])->bool:
        '''
           检查对象是否已经注册
        '''
        if isinstance(objc,str):
            return objc in self._registered_types or objc in self._registered_modifiers
        elif isinstance(objc,bgc.Character):
            return objc in self._registered_chars
        elif isinstance(objc,bgc.Skill):
            return objc in self._registered_skills
        elif isinstance(objc,bgc.Item): #type:ignore
            return objc in self._registered_items
        else:
            raise ValueError('只能检查角色，技能，物品或者事件类型')
    
    def handle_message(self, msg:'GameMessage')->Tuple[int,EventResult,str]:
        '''
           处理消息
           用于消息处理器调用，根据消息阶段调用对应的处理函数
           
           参数：msg:消息体
        '''
        if msg.phase == MessagePhase.PRE:
            handler = self._pre_handlers.get(msg.type)
        elif msg.phase == MessagePhase.MAIN:
            handler = self.ev_handlers.get(msg.type)
        elif msg.phase == MessagePhase.POST:
            handler = self._post_handlers.get(msg.type)
        else:
            raise ValueError('无效的消息阶段')
            
        if handler:
            return handler(msg)  # 正常调用处理函数
        else:
            raise ValueError(f'未注册{msg.type}的{msg.phase.name}阶段处理函数')                               

    def handle_modifier(self, msg: 'GameMessage', modifier_type: str,val:Any)-> Tuple[Any,Any,bool]: #raw_val,modified_val,is_success
        """处理自定义modifier"""
        handler = self._custom_modifiers.get(modifier_type)
        if handler:
            return handler(msg,val)
        else:
            raise ValueError(f"未注册modifier类型: {modifier_type}")

    def clr(self):
        '''
           清除所有注册的事件与对象
        '''
        self._pre_handlers.clear()
        self.ev_handlers.clear()
        self._post_handlers.clear()
        self._registered_types.clear()
        self._registered_chars.clear()
        self._registered_skills.clear()
        self._registered_items.clear()
        self.chars.clear()
        self.skills.clear()
        self.items.clear()
        logger.info('已经清除所有注册的事件与对象')

#基本的几个事件类型的基处理器，不建议修改
BASE_MSG_HANDLER=Handler()

@BASE_MSG_HANDLER.handles('ATTACK')
def _handle_attack(msg: 'GameMessage') ->Tuple[int, EventResult, str]: #type: ignore
    '''处理攻击事件，主要是根据消息计算好是否暴击等特性，以及计算最终伤害值并进入伤害处理'''
    if msg.receiver and msg.sender:
        ret_msg=msg.create(
            messagechain=msg.messagechain,
            type='DAMAGE',
            sender=msg.sender,
            receiver=msg.receiver,
            value=0,
            extra=[],
        )
        
        #基本伤害计算公式:max(a.atk-b.def,0)
        dmg=max(msg.sender.i.attack-msg.receiver.i.defense,0)
        if msg.get_value()>0:
            dmg=msg.get_value()
        ret_msg.add_extra(MessageExtra.RAW_DAMAGE,dmg)
        
        #处理暴击
        if random.randint(1,100)<=msg.sender.i.critical:
            dmg*=(msg.sender.i.critical_damage)//100
            ret_msg.add_extra(MessageExtra.CRIT,True)
            print("触发暴击！")
        else:
            ret_msg.add_extra(MessageExtra.CRIT,False)
        ret_msg.add_extra(MessageExtra.AFTER_CRIT_DAMAGE,dmg)
        
        #处理闪避
        if random.randint(100,200)<=100+msg.receiver.i.evasion:
            ret_msg.add_extra(MessageExtra.DODGE,True)
            dmg=0
            print("触发闪避！")
        else:
            ret_msg.add_extra(MessageExtra.DODGE,False)
        
        #添加最终伤害消息，然后返回
        ret_msg.value=dmg
        msg.messagechain.i.manager.acceptmsg(ret_msg)
        return (0,EventResult.CONTINUE,"无错误")    
    
    return (-1,EventResult.SKIP,"[攻击事件处理]错误:没有攻击者或接收者")

@BASE_MSG_HANDLER.handles('DAMAGE')
def _handle_damage(msg: 'GameMessage') -> Tuple[int, EventResult, str]: #type: ignore
    """具体伤害处理逻辑"""
    if msg.receiver and msg.value:  # 需要有接受者
        # 确保msg.value是int类型
        damage_value = msg.value(msg) if callable(msg.value) else msg.value
        msg.receiver.i.change_attribute('current_hp', -damage_value)
        print(f"[伤害处理] {msg.receiver.i.name} 受到 {damage_value} 点伤害，剩余HP: {msg.receiver.i.current_hp}")
        return (0,EventResult.CONTINUE,"无错误")
    return (-1,EventResult.RE_INPUT,"[伤害处理]错误:没有接受者或无效伤害值")

@BASE_MSG_HANDLER.handles('HEAL')
def _handle_heal(msg: 'GameMessage') -> Tuple[int, EventResult, str]: #type: ignore
    """治疗处理逻辑"""
    if msg.receiver and msg.value:  # 需要有接受者
        # 确保msg.value是int类型
        heal_value = msg.value(msg) if callable(msg.value) else msg.value
        if heal_value > 0:
            msg.receiver.i.change_attribute('current_hp', heal_value)
            print(f"[治疗处理] {msg.receiver.i.name} 恢复 {heal_value} 点生命，剩余HP: {msg.receiver.i.current_hp}")
            return (0, EventResult.CONTINUE, "无错误")
    return (-1, EventResult.RE_INPUT, "[治疗处理]错误:没有接受者或无效治疗值")

#默认直接定义一个主处理器,继承自基本消息类型的基处理器  
Mainhandler=Handler(BASE_MSG_HANDLER) 

class EventEffectProtocal(Protocol):
    reg_type:str
    def reg(self, handler: 'Handler') -> None:...

class ListenerProtocal(Protocol):
    uuid:uuid.UUID
    reg_type:str
    def update(self, msg: 'GameMessage') -> Any: ...
    def reg(self, handler: 'Handler') -> None: ...


#消息处理器，需要绑定中心事件处理器对象使用。
class MessageManager:
    def __init__(self,handler:Handler=Mainhandler):
        self.listener:List[ListenerProtocal]=[]
        self.messagechain=MessageChain(self)
        self.base_handler=handler
        self.handler=Handler(self.base_handler)
        self.processor=MessageProcessor(self)
        self.uuid=uuid.uuid4()
        
    def register(self, objec: 'ListenerProtocal') -> None:
        '''
           注册监听器
           
           参数：objec:可监听对象(含update方法)
        '''
        if not hasattr(objec, 'update') or not callable(objec.update):
            raise ValueError('''对象没有update方法,不是能够接受消息的对象,不能在事件管理器注册监听器。
                             [尝试在Handler注册?]''')
            
        self.listener.append(objec)
        if (hasattr(objec, 'reg') and callable(objec.reg) 
            and hasattr(objec, 'reg_type') 
            and not self.handler.is_reg(objec.reg_type)):
            objec.reg(self.handler)
        logger.info(f'成功注册{objec},UUID:{objec.uuid}')
            
    def unregister(self, objec: 'ListenerProtocal') -> None:
        self.listener.remove(objec)
        logger.info(f'移除{objec}')

    def clear(self):
        '''清空监听器'''
        self.listener.clear()
        logger.info('清空所有监听器')
    
    def reset(self):
        """重置消息管理器"""
        self.clear()
        self.handler=Handler(self.base_handler)
        self.messagechain.clear()
        logger.info("重置消息管理器")
    
    def acceptmsg(self, msg:'GameMessage'): #一般消息左插入
            '''
            接受一般消息，并插入到队列左端，即立刻执行
            自动处理NONE阶段消息的拆分
            '''
            if msg.phase == MessagePhase.NONE:
                pre_msg, main_msg, post_msg = msg.splitself()
                # 注意顺序：POST -> MAIN -> PRE (因为左插入是倒序的)
                self.messagechain.i.acceptmsg(post_msg)
                self.messagechain.i.acceptmsg(main_msg)
                self.messagechain.i.acceptmsg(pre_msg)
            else:
                self.messagechain.i.acceptmsg(msg)
            logger.info(f"接收到{msg.type}消息")
    def acceptmsgp(self, msg:'GameMessage'): #延迟消息右插入
        '''接受延迟消息，插入到队列右端
        自动处理NONE阶段消息的拆分
        '''
        if msg.phase == MessagePhase.NONE:
            pre_msg, main_msg, post_msg = msg.splitself()
            # 注意顺序：PRE -> MAIN -> POST (因为右插入是正序的)
            self.messagechain.i.acceptmsgp(pre_msg)
            self.messagechain.i.acceptmsgp(main_msg) 
            self.messagechain.i.acceptmsgp(post_msg)
        else:
            self.messagechain.i.acceptmsgp(msg)
        logger.info(f"\n接收{msg.type}延迟消息")

    def broadcast(self,msg:'GameMessage',mode:str='all',certain:Optional[Set[ListenerProtocal]]=None):
        '''广播消息(全量)'''
        def main_action(listener:ListenerProtocal,msg:'GameMessage'):
            if listener.update(msg):
                msg.messagechain.i.update_reacted_objects(listener)
                logger.info(f'[广播] {listener} 已处理消息')
            else:
                logger.info(f'[广播] {listener} 无法处理消息或不响应此消息')
                # 这里可以添加一些错误处理逻辑，例如记录错误
                # 例如：self._handle_broadcast_error(listener, msg)
                
            
        match mode:
            case 'all':
                logger.info(f'>全量< 广播消息[{msg.type}|{msg.phase}]')
                for k in self.listener:
                    main_action(k,msg)
            case 'new':
                logger.info(f'>不重复对象< 广播消息[{msg.type}|{msg.phase}]')
                for k in self.listener:
                    if not msg.messagechain.i.is_reacted(k):
                        main_action(k,msg)
            case 'certain':
                if certain:
                    logger.info(f'>指定对象< 广播消息[{msg.type}|{msg.phase}]')
                    for k in certain:
                        main_action(k,msg)
            case 'certainnew':
                if certain:
                    logger.info(f'>指定对象(不重复)< 广播消息[{msg.type}|{msg.phase}]')
                    for k in certain:
                        if not msg.messagechain.i.is_reacted(k):
                            main_action(k,msg)
            case 'except':
                if certain:
                    logger.info(f'>排除指定对象< 广播消息[{msg.type}|{msg.phase}]')
                    for k in self.listener:
                        if k not in certain:
                            main_action(k,msg)
            case 'exceptnew':
                if certain:
                    logger.info(f'>排除指定对象(不重复)< 广播消息[{msg.type}|{msg.phase}]')
                    for k in self.listener:
                        if k not in certain and not msg.messagechain.i.is_reacted(k):
                            main_action(k,msg)
            case _:
                raise ValueError('无效的广播模式')

    def handle(self, msg: 'GameMessage') -> bool:
        '''处理消息并返回是否继续执行'''
        logger.info(f"处理 {msg.type} 类型 {msg.phase}阶段 消息")
        result = self.handler.handle_message(msg)
        
        # 处理返回结果
        if len(result) >= 2:
            error_code, event_result, *error_info = result
            error_msg = error_info[0] if error_info else ""
            
            if error_code != 0:
                logger.info(f"[错误] {error_msg}")
                
            if event_result == EventResult.STOP:
                logger.info("停止执行后续消息")
                self.messagechain.i.clear()
                return False
            elif event_result == EventResult.SKIP:
                logger.info(f"跳过{msg.type}类型的所有阶段消息")
                self._skip_current_event(msg)
                return False
            elif event_result == EventResult.RE_INPUT:
                logger.info("需要重新输入消息")
                return False
                
        return True

    def _skip_current_event(self, msg: 'GameMessage'):
        '''跳过当前事件的所有阶段消息,包括嵌套'''
        while self.messagechain.i:
            next_msg = self.messagechain.i.pop()
            if next_msg and next_msg.type == msg.type and next_msg.phase == MessagePhase.POST:
                break 
   
    def execte_single(self):
        '''执行消息队列中的单个消息'''
        if self.messagechain.i:
            msg = self.messagechain.i.pop()
            if msg and msg.validate_check_body():
                self.broadcast(msg)
                if (not self.processor.process(msg)) or (not self.handle(msg)):  # 根据handle返回值决定是否继续
                    return False
                return True
        return False
 
    def execte(self):
        '''执行消息队列中的所有消息'''
        while self.messagechain.i and self.execte_single():
            pass
        #执行结束后，初始化消息链，以重用
        self.messagechain.i.clear()
    def __bool__(self):
        '''
           返回消息队列是否为空
        '''
        return bool(self.messagechain)
    
    def __len__(self):
        '''
           返回消息队列长度
        '''
        return len(self.messagechain)

#消息加工器，用于应用modifier
class MessageProcessor:
    def __init__(self,manager:'MessageManager'):
        self.manager:MessageManager=manager
    
    def process(self,msg:'GameMessage')->bool:
        '''
           处理消息
        '''
        logger.info(f'消息[{msg.type}|{msg.phase}]的modifiers有:{msg.modifiers}')
        logger.info(f'正在加工消息[{msg.type}|{msg.phase}]')
        if not msg.modifiers:
            return True
        for mod_type,val in msg.modifiers:
            if not self._apply_modifier(msg,mod_type,val):
                msg.clr_modifiers()
                return False
        msg.clr_modifiers()
        return True
    def _apply_modifier(self,msg:'GameMessage',mod_type:Union[str,ModifierType],val:Any)->bool:
        '''
           应用modifier,并广播修改消息和修改后的消息。
           对于修改后的消息，不对已经相应过的对象进行广播。
        '''
        modify_type:Union[str,ModifierType]=mod_type
        raw_value:Any=None
        modify_value:Any= val(msg) if callable(val) else val
        
        
        match mod_type:
            case ModifierType.SET_VALUE:
                raw_value=msg.value
                msg.value=modify_value
            case ModifierType.SET_SENDER:
                raw_value=msg.sender
                msg.sender=modify_value
            case ModifierType.SET_RECEIVER:
                raw_value=msg.receiver
                msg.receiver=modify_value
            case ModifierType.UPDATE_EXTRA:
                if not (isinstance(val, tuple) and len(val) == 2 and isinstance(val[0], MessageExtra)):
                    logger.info(f'因格式错误而更新Extra信息失败:{val}')
                    return False
                if msg.extra:
                    raw_value = next((v for k, v in msg.extra if k == val[0]), None)
                    if raw_value:
                        msg.rmv_extra(val[0])
                    msg.add_extra(*val)
                else:
                    msg.add_extra(*val)
                    raw_value=None
            case ModifierType.REMOVE_EXTRA:
                if not isinstance(val,MessageExtra):
                    logger.info(f'因格式错误而移除Extra信息失败:{val}')
                    return False
                if msg.extra:
                    raw_value = next((v for k, v in msg.extra if k == val), None)
                    msg.rmv_extra(val)
            case ModifierType.REMOVE_MODIFIER:
                if not isinstance(val, Union[str,ModifierType]):
                    logger.info(f'因格式错误而移除Modifier信息失败:{val}')
                    return False
                if msg.modifiers:
                    raw_value = next(((k,v) for k, v in msg.modifiers if k == val), None)
                    msg.rmv_modifier(raw_value)
                    
            case _:
                if isinstance(mod_type,str) and self.manager.handler.is_reg(mod_type):
                    raw_value,modify_value,result=self.manager.handler.handle_modifier(msg,mod_type,val)
                    if not result:
                        logger.info(f'应用修饰失败:{mod_type}')
                        return False
        #广播修改后的消息(由于动态修改，所以直接广播msg即可，不需要再创建)
        self.manager.broadcast(msg,mode='new')
        #全量广播修改(MODIFY)消息
        modify_msg=msg.create(
            messagechain=msg.messagechain,
            type='MODIFY',
            sender=msg.sender,
            receiver=msg.receiver,
            value=modify_value,
            extra=[(MessageExtra.MODIFY_TYPE,modify_type),(MessageExtra.MODIFY_VALUE,modify_value),(MessageExtra.RAW_VALUE,raw_value)]
        )
        self.manager.broadcast(modify_msg,mode='all')
        return True
    

#游戏消息部分,用于事件驱动模式的消息传递
class MessageChain:
    def __init__(self,manager:'MessageManager'):
        self.manager:'MessageManager'=manager
        self.queue:Deque[GameMessage]=deque() #消息队列
        self.uuid=uuid.uuid4() #消息链ID
        self.msgchains:List[GameMessage]=[] #记录消息链
        self.reacted_objects:DefaultDict[ListenerProtocal,int]=defaultdict(int) #已处理的对象及其次数
        self.variables:Dict[str,Dict[str,Any]]={} #消息链变量表
        self._api=MessageChainAPI(self) #API接口
    
    @property
    def i(self):
        return self._api
    
    def add_variable(self,sign:str, key: str, value: Any) -> None:
        """添加或更新消息链变量"""
        if sign not in self.variables:
            self.variables[sign] = {}
        self.variables[sign][key] = value
        logger.info(f'添加消息链变量: {sign}.{key} = {value}')

    def get_variable(self,sign:str, key: str, default: Any = None) -> Any:
        """获取消息链变量"""
        return self.variables.get(sign, {}).get(key, default)
    
    def rmv_variable(self, sign: str, key: str) -> Tuple[bool, Any]:
        """移除消息链变量
        参数:
            sign: 作用域签名
            key: 要移除的变量名
        返回:
            (是否成功移除, 变量值)
        """
        if sign in self.variables and key in self.variables[sign]:
            value = self.variables[sign].pop(key)
            return (True, value)
        return (False, None)
                
    def clr_variables(self,sign:Optional[str]=None) -> None:
        """清空消息链变量"""
        if not sign:
            self.variables.clear()
            logger.info('消息链变量表已清空')
        else:
            if sign in self.variables:
                self.variables[sign].clear()
                logger.info(f'消息链变量表[{sign}]已清空')
            else:
                logger.info(f'消息链变量表[{sign}]不存在')
    
    def exists_variable(self, sign: str, key: str) -> bool:
        """检查消息链变量是否存在"""
        return sign in self.variables and key in self.variables[sign]      
        
        
    def acceptmsg(self,msg:'GameMessage'): #一般消息左插入
        '''
           接受一般消息，并插入到队列左端
        '''
        self.queue.appendleft(msg)
    
    def acceptmsgp(self,msg:'GameMessage'): #优先消息右插入
        '''
           接受优先消息，插入到队列右端
        '''
        self.queue.append(msg)

    def pop(self):
        '''
           弹出消息
        '''
        return self.queue.popleft() if self.queue else None
    
    def clear(self):
        '''
           清空消息链
        '''
        self.queue.clear()
        logger.info('消息链已经清空')
        
    def reset(self):
        '''
           重置所有消息链相关的变量
        '''
        self.clear()
        self.msgchains.clear()
        self.reacted_objects.clear()
        self.variables.clear()
        logger.info('消息链已重置')
    def __len__(self):
        '''
           返回消息队列长度
        '''
        return len(self.queue)
    def __bool__(self):
        '''
           返回消息队列是否为空
        '''
        return bool(self.queue)

class MessageChainAPI:
    def __init__(self, chain: MessageChain) -> None:
        self.chain = chain
        self._queue = chain.queue
        self._uuid = chain.uuid
        self._msgchains = chain.msgchains
        self._reacted_objects = chain.reacted_objects
        self._manager = chain.manager
        self._variables = chain.variables
        
    @property
    def length(self):
        return len(self._queue)
    @property
    def empty(self):
        return not self._queue
    @property
    def uuid(self):
        return self._uuid
    @property
    def reacted_objects(self):
        return self._reacted_objects
    @property
    def manager(self):
        return self._manager
    @property
    def queue(self):
        return self._queue
      
    #队列消息部分  
    def pop(self):
        return self.chain.pop() if self.chain else None
    def clear(self):
        self.chain.clear()
    def acceptmsg(self,msg:'GameMessage'): #一般消息左插入
        self.chain.acceptmsg(msg)
    def acceptmsgp(self,msg:'GameMessage'): #优先消息右插入
        self.chain.acceptmsgp(msg) 
    def contains_type(self, msg_type: str) -> bool:
        """检查队列中是否包含指定类型的消息"""
        return any(msg.type == msg_type for msg in self._queue)
    def find_message(self, msg_type: str,phase:MessagePhase = MessagePhase.NONE,th :int = 1) -> Optional['GameMessage']:
        """查找队列中指定类型和阶段的第th条消息"""
        for msg in self._queue:
            if msg.type == msg_type and msg.phase == phase:
                th-=1
                if th==0:
                    return msg
        return None
    def find_all_messages(self, msg_type: str,phase:MessagePhase = MessagePhase.NONE) -> List['GameMessage']:
        """查找队列中指定类型和阶段的所有消息"""
        return [msg for msg in self._queue if msg.type == msg_type and msg.phase == phase]
    
    #reacted已处理对象部分
    def update_reacted_objects(self, obj: ListenerProtocal) -> None:
        """更新已处理的对象及其次数"""
        self._reacted_objects[obj] += 1
    def clr_reacted_objects(self) -> None:
        """清空已处理的对象及其次数"""
        self._reacted_objects.clear()
    def get_reacted_objects(self,objec:ListenerProtocal) -> int:
        """获取已处理的对象及其次数"""
        return self._reacted_objects.get(objec,0)    
    def is_reacted(self,objec:ListenerProtocal) -> bool:
        """检查对象是否已经处理过"""
        return objec in self._reacted_objects
   
    #消息链部分 
    def update_msgchains(self, msg: 'GameMessage') -> None:
        """更新消息链"""
        self._msgchains.append(msg)    
    def clr_msgchains(self) -> None:
        """清空消息链"""
        self._msgchains.clear()
    def find_msgchain(self, msg_type: str,th: int=1) -> Optional['GameMessage']:
        """查找消息链中指定类型的第th条消息"""
        for msg in self._msgchains:
            if msg.type == msg_type:
                th-=1
                if th==0:
                    return msg
        return None
    
    #变量部分(由于面向用户编写，所以简化函数名)
    def vadd(self,sign:str, key: str, value: Any) -> None:
        """添加或更新消息链变量"""
        self.chain.add_variable(sign, key, value)
    def vget(self,sign:str, key: str, default: Any = None) -> Any:
        """获取消息链变量"""
        return self.chain.get_variable(sign, key, default)
    def vrmv(self, sign: str, key: str) -> Tuple[bool, Any]:
        """移除消息链变量"""
        return self.chain.rmv_variable(sign, key)
    def vpop(self,sign:str, key: str, default: Any = None) -> Any:
        """弹出消息链变量"""
        return self.vrmv(sign, key)[1] or default
    def vclr(self,sign:Optional[str]=None) -> None:
        """清空消息链变量"""
        self.chain.clr_variables(sign)
    def vall(self,sign:Optional[str]=None) -> Dict[str, Any]:
        """获取消息链变量"""
        return self.chain.variables
    def vhave(self, sign: str, key: str) -> bool:
        """检查消息链变量是否存在"""
        return self.chain.exists_variable(sign,key)
    
    #其他
    def clr(self):
        """初始化所有变量"""
        self.chain.reset()
        
    def __bool__(self):
        return bool(self._queue)
    def __len__(self):
        return len(self._queue)
      
@dataclass
class GameMessage:
    messagechain:MessageChain #消息链
    type:str #消息类型，如ATTACK等
    value:Union[int, Callable[['GameMessage'], int]]=0 #消息基本值
    extra:Optional[List[Tuple[MessageExtra,Any]]]=None #额外信息
    sender:Optional[bgc.Character]=None #发送者
    receiver:Optional[bgc.Character]=None #接收者
    modifiers:Optional[List[Tuple[Union[str,ModifierType], Union[int, Callable[['GameMessage'], int]]]]]=None #消息修饰器(唯一可修改，其他的必须由消息加工阶段根据修饰器进行修改)
    phase:MessagePhase=MessagePhase.NONE #消息阶段.注意：不应该直接使用，由消息处理器决定
    check_body:Optional['GameMessage']=None #检查消息体,用于不同Phase的消息同步，一般是MAIN的检查消息体为PRE，POST的检查消息体为MAIN。
    
    def splitself(self) -> Tuple['GameMessage', 'GameMessage', 'GameMessage']:#将消息拆分为PRE,MAIN和POST,返回三个消息
        if self.phase==MessagePhase.NONE:
            pre=self.create(self.messagechain,self.type,self.value,self.extra,self.sender,self.receiver,self.modifiers,MessagePhase.PRE,self.check_body)
            main=self.create(self.messagechain,self.type,self.value,self.extra,self.sender,self.receiver,self.modifiers,MessagePhase.MAIN,pre)
            post=self.create(self.messagechain,self.type,self.value,self.extra,self.sender,self.receiver,self.modifiers,MessagePhase.POST,main)
            return pre,main,post
        else:
            raise ValueError('消息已经经过拆分')
    def modify(self, modifier: Tuple[Union[str,ModifierType], Union[int, Callable[['GameMessage'], int]]]):  # 修改这里
        if self.modifiers:
            self.modifiers.append(modifier)
        else:
            self.modifiers = [modifier]
            
    def get_value(self) -> int:
        """安全获取value值的方法"""
        return self.value(self) if callable(self.value) else self.value
    
    def next_phase(self) -> MessagePhase: #获取下一个消息阶段
        return MessagePhase((self.phase.value + 1)%4)
    
    def rmv_modifier(self,modifier: Tuple[Union[str,ModifierType], Union[int, Callable[['GameMessage'], int]]]): #清除修饰器
        if self.modifiers:
            self.modifiers.remove(modifier)
    
    def clr_modifiers(self): #清除所有修饰器
        self.modifiers=[]
    
    def add_extra(self, extra_type: MessageExtra, value: Any) -> None:
        """添加extra信息并进行类型检查"""
        if extra_type.expected_type is not Any:
            if not isinstance(value, extra_type.expected_type): #type:ignore
                raise TypeError(f"{extra_type.key} 的值必须是 {extra_type.expected_type.__name__} 类型")
            
        if self.extra is None:
            self.extra = []
        self.extra.append((extra_type, value))
    
    def get_extra(self, extra_type: MessageExtra) -> Any:
        """获取指定类型的extra值"""
        if self.extra:
            for key, value in self.extra:
                if key == extra_type:
                    if not isinstance(value, extra_type.expected_type): #type:ignore
                        raise TypeError(f"{extra_type.key} 的值应该是 {extra_type.expected_type.__name__} 类型")
                    return value
        return None
    
    def rmv_extra(self, extra_type: MessageExtra) -> None:
        """清除指定类型的extra值"""
        if self.extra:
            self.extra = [(key, value) for key, value in self.extra if key != extra_type]
            
    def clr_extras(self) -> None:
        """清除所有extra值"""
        self.extra = []
    
    def create(self, messagechain: MessageChain, type: str, 
              value: Union[int, Callable[['GameMessage'], int]] = 0,
              extra: Optional[List[Tuple[MessageExtra, Any]]] = None,
              sender: Optional[bgc.Character] = None,
              receiver: Optional[bgc.Character] = None,
              modifiers: Optional[List[Tuple[Union[str,ModifierType], Union[int, Callable[['GameMessage'], int]]]]] = None,
              phase: MessagePhase = MessagePhase.NONE,
              check_body: Optional['GameMessage'] = None) -> 'GameMessage':
        # 确保value是int或返回int的回调函数
        if callable(value):
            # 添加类型检查确保回调函数返回int
            def checked_value_func(msg: 'GameMessage') -> int:
                result = value(msg)
                if not isinstance(result, int): #type:ignore
                    raise TypeError("回调函数必须返回int类型")
                return result
            actual_value = checked_value_func
        else:
            actual_value = value
            
        return GameMessage(messagechain, type, actual_value, extra, sender, receiver, modifiers, phase, check_body)

    def copy(self):
        return copy.deepcopy(self)
    
    def validate_check_body(self) -> bool:
        """校验check_body与当前消息的一致性"""
        if not self.check_body:
            return True
            
        # 类型和消息链校验
        if (self.type != self.check_body.type or self.messagechain != self.check_body.messagechain):
            return False
            
        # 修改的value,extra,sender,receiver,modifiers等均应该继承
        self.value = self.check_body.value
        self.extra = self.check_body.extra
        self.sender = self.check_body.sender
        self.receiver = self.check_body.receiver
        self.modifiers = self.check_body.modifiers

        return True