"""
PromptService 单元测试
测试核心流程：获取提示词
"""
import pytest
from services.prompt_service import PromptService
from models.prompt_template import PromptTemplate
from models.trader import Trader
from sqlmodel import select


class TestPromptService:
    """PromptService 核心功能测试"""
    
    def test_get_prompt_by_name_exists(self, settings, db_session):
        """测试获取存在的提示词模板"""
        prompt_service = PromptService(settings)
        
        # 创建测试数据
        template = PromptTemplate(
            name="test_template",
            content="这是测试提示词内容",
            description="测试描述"
        )
        db_session.add(template)
        db_session.commit()
        
        # 测试获取
        result = prompt_service.get_prompt_by_name("test_template")
        assert result == "这是测试提示词内容"
    
    def test_get_prompt_by_name_not_exists(self, settings):
        """测试获取不存在的提示词模板"""
        prompt_service = PromptService(settings)
        
        result = prompt_service.get_prompt_by_name("non_existent_template")
        assert result is None
    
    def test_get_prompt_by_trader_with_custom_override(self, settings, db_session):
        """测试交易员使用自定义提示词覆盖基础提示词"""
        prompt_service = PromptService(settings)
        
        # 创建基础模板
        base_template = PromptTemplate(
            name="default",
            content="基础提示词",
            description="基础模板"
        )
        db_session.add(base_template)
        
        # 创建交易员（需要先有用户和AI模型、交易所）
        from models.user import User
        from models.ai_model import AIModel
        from models.exchange import Exchange
        from decimal import Decimal
        
        import uuid
        user = User(
            email=f"test_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="test_hash"
        )
        db_session.add(user)
        db_session.flush()
        
        ai_model = AIModel(
            user_id=str(user.id),
            name="test_model",
            provider="openai",
            enabled=True
        )
        db_session.add(ai_model)
        db_session.flush()
        
        exchange = Exchange(
            user_id=str(user.id),
            name="test_exchange",
            type="cex",
            enabled=True
        )
        db_session.add(exchange)
        db_session.flush()
        
        trader = Trader(
            user_id=str(user.id),
            name="test_trader",
            ai_model_id=str(ai_model.id),
            exchange_id=str(exchange.id),
            initial_balance=Decimal("10000"),
            custom_prompt="自定义提示词",
            override_base_prompt=True
        )
        db_session.add(trader)
        db_session.commit()
        
        # 测试获取
        result = prompt_service.get_prompt_by_trader(str(trader.id))
        assert result == "自定义提示词"
    
    def test_get_prompt_by_trader_with_base_template(self, settings, db_session):
        """测试交易员使用基础模板"""
        prompt_service = PromptService(settings)
        
        # 创建唯一名称的模板，避免与现有数据冲突
        template_name = "test_base_template"
        base_template = PromptTemplate(
            name=template_name,
            content="基础提示词内容",
            description="基础模板"
        )
        db_session.add(base_template)
        db_session.flush()
        
        # 创建交易员
        from models.user import User
        from models.ai_model import AIModel
        from models.exchange import Exchange
        from decimal import Decimal
        
        import uuid
        user = User(
            email=f"test2_{uuid.uuid4().hex[:8]}@example.com",
            password_hash="test_hash"
        )
        db_session.add(user)
        db_session.flush()
        
        ai_model = AIModel(
            user_id=str(user.id),
            name="test_model",
            provider="openai",
            enabled=True
        )
        db_session.add(ai_model)
        db_session.flush()
        
        exchange = Exchange(
            user_id=str(user.id),
            name="test_exchange",
            type="cex",
            enabled=True
        )
        db_session.add(exchange)
        db_session.flush()
        
        trader = Trader(
            user_id=str(user.id),
            name="test_trader2",
            ai_model_id=str(ai_model.id),
            exchange_id=str(exchange.id),
            initial_balance=Decimal("10000"),
            system_prompt_template=template_name
        )
        db_session.add(trader)
        db_session.commit()
        
        # 测试获取
        result = prompt_service.get_prompt_by_trader(str(trader.id))
        assert result == "基础提示词内容"
    
    def test_get_prompt_by_trader_not_exists(self, settings):
        """测试获取不存在的交易员的提示词"""
        prompt_service = PromptService(settings)
        
        result = prompt_service.get_prompt_by_trader("non_existent_trader_id")
        # 应该返回默认提示词或 None
        assert result is None or isinstance(result, str)

