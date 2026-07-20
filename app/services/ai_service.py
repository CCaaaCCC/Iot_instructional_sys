"""AI 对话服务层：会话管理 + 配额 + 双模型切换 + 流式生成。

设计要点：
- 使用 openai SDK（DeepSeek 兼容 OpenAI API 格式），AsyncOpenAI 客户端单例
- 双模型智能切换：关键词命中 → deepseek-reasoner，否则 → deepseek-chat
- 配额独立计数表（ai_quota_usage），删除会话不影响配额
- 流式响应：async generator yield SSE 格式数据
- 会话隔离：用户只能访问自己的会话（user_id 校验）
- 内容安全：系统提示词约束（小学场景语言通俗 + 拒绝不当话题）
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import AsyncGenerator

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_quota_usage import AiQuotaUsage
from app.models.chat_message import ChatMessage
from app.models.chat_session import ChatSession
from app.models.enums import UserRole
from app.schemas.chat import ChatContext

logger = logging.getLogger(__name__)

# 触发 reasoner 模型的关键词（复杂推理场景）
_REASONER_KEYWORDS: tuple[str, ...] = (
    "为什么",
    "分析",
    "解释原理",
    "设计",
    "制定",
    "推理",
    "推导",
    "对比",
    "评估",
    "原理",
    "解释一下",
    "深入",
    "论证",
)

# 会话保留天数（init_db 启动时清理）
SESSION_RETENTION_DAYS = 180

# AsyncOpenAI 客户端单例（懒加载）
_client: AsyncOpenAI | None = None


def get_client() -> AsyncOpenAI:
    """获取 AsyncOpenAI 客户端单例。

    若 DEEPSEEK_API_KEY 未配置，抛出 RuntimeError。
    """
    global _client
    if _client is None:
        if not settings.DEEPSEEK_API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY is not configured")
        _client = AsyncOpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url=settings.DEEPSEEK_BASE_URL,
            timeout=settings.AI_REQUEST_TIMEOUT,
        )
    return _client


def is_ai_configured() -> bool:
    """检查 AI 是否已配置（API Key 非空）。"""
    return bool(settings.DEEPSEEK_API_KEY)


# ---------------------------------------------------------------------------
# SSE 事件格式化
# ---------------------------------------------------------------------------

def sse_event(event_type: str, data: dict) -> str:
    """格式化 SSE 事件：data: {json}\n\n。公开供 router 复用。"""
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# 模型选择
# ---------------------------------------------------------------------------

def select_model(message: str) -> str:
    """根据用户消息关键词选择模型。

    命中推理关键词 → deepseek-reasoner，否则 → deepseek-chat。
    简单可预测、零额外 API 成本。
    """
    for keyword in _REASONER_KEYWORDS:
        if keyword in message:
            return settings.DEEPSEEK_MODEL_REASONER
    return settings.DEEPSEEK_MODEL_CHAT


# ---------------------------------------------------------------------------
# 系统提示词构建
# ---------------------------------------------------------------------------

def build_system_prompt(user, context: ChatContext | None = None) -> str:
    """构建系统提示词：角色人设 + 用户身份 + 页面上下文。

    根据 user.role 区分学生/教师人设，确保语言风格与内容安全适合小学场景。
    """
    display_name = user.display_name or user.username

    if user.role == UserRole.student:
        persona = (
            f"你是「棚棚小助手」，智慧大棚学习平台的 AI 学习助手，面向小学生。\n\n"
            "回答原则：\n"
            "1. 语言通俗、耐心，多用比喻和生活例子，避免专业术语\n"
            "2. 只回答与大棚种植、传感器、科学实验、学习任务、植物生长相关的问题\n"
            "3. 涉及不当话题（暴力、色情、政治敏感等）时，礼貌引导回学习话题\n"
            "4. 鼓励学生动手观察和思考，不只给答案，引导探索\n"
            "5. 回答控制在 300 字以内，适合小学生阅读\n\n"
            f"当前用户：{display_name}，学生"
        )
        if user.group_id:
            persona += f"（第 {user.group_id} 组）"
    else:
        persona = (
            f"你是智慧大棚教学平台的 AI 教学助手，面向小学教师。\n\n"
            "回答原则：\n"
            "1. 语言专业简洁，提供可操作的建议\n"
            "2. 协助备课、任务设计、实验方案、学情分析、批阅参考\n"
            "3. 内容贴合小学劳动课/科学课大纲\n"
            "4. 涉及不当话题时礼貌拒绝\n"
            "5. 回答控制在 500 字以内，必要时用 Markdown 结构化\n\n"
            f"当前用户：{display_name}，{user.role.value if hasattr(user.role, 'value') else user.role}"
        )

    # 页面上下文注入
    if context:
        persona += f"\n\n当前页面：{context.route_name}"
        if context.page_data:
            try:
                page_data_json = json.dumps(context.page_data, ensure_ascii=False, default=str)
                # 限制 page_data 长度，避免 token 浪费
                if len(page_data_json) > 1000:
                    page_data_json = page_data_json[:1000] + "...(已截断)"
                persona += f"\n页面数据：{page_data_json}"
            except (TypeError, ValueError):
                logger.warning("Failed to serialize page_data for AI context")

    return persona


# ---------------------------------------------------------------------------
# 会话管理
# ---------------------------------------------------------------------------

def create_session(db: Session, user, title: str | None = None) -> ChatSession:
    """创建新会话。title 为 None 时使用默认标题。"""
    session = ChatSession(
        user_id=user.id,
        title=title or "新对话",
        role_hint=user.role.value if hasattr(user.role, "value") else str(user.role),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def list_sessions(
    db: Session, user, skip: int = 0, limit: int = 20
) -> list[ChatSession]:
    """列出用户的所有会话（按更新时间倒序）。"""
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def get_session(db: Session, session_id: int, user) -> ChatSession | None:
    """获取会话并校验归属（用户只能访问自己的会话）。"""
    session = db.get(ChatSession, session_id)
    if session is None or session.user_id != user.id:
        return None
    return session


def get_session_messages(
    db: Session, session_id: int, user, limit: int = 50
) -> list[ChatMessage]:
    """获取会话消息（按时间正序，含 user 和 assistant）。"""
    # 先校验归属
    session = get_session(db, session_id, user)
    if session is None:
        return []
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .limit(limit)
    )
    return list(db.execute(stmt).scalars().all())


def delete_session(db: Session, session_id: int, user) -> bool:
    """删除会话及其所有消息（级联删除）。返回是否成功。"""
    session = get_session(db, session_id, user)
    if session is None:
        return False
    db.delete(session)
    db.commit()
    return True


def rename_session(db: Session, session_id: int, user, title: str) -> ChatSession | None:
    """重命名会话。"""
    session = get_session(db, session_id, user)
    if session is None:
        return None
    session.title = title
    db.commit()
    db.refresh(session)
    return session


def get_last_message_preview(db: Session, session_id: int) -> str | None:
    """获取会话最近一条消息的内容预览（截断 50 字符）。"""
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(1)
    )
    msg = db.execute(stmt).scalar_one_or_none()
    if msg is None:
        return None
    content = msg.content.strip()
    return content[:50] + "..." if len(content) > 50 else content


# ---------------------------------------------------------------------------
# 配额管理
# ---------------------------------------------------------------------------

def get_quota(db: Session, user) -> dict:
    """查询用户今日配额使用情况。"""
    today = date.today()
    stmt = select(AiQuotaUsage).where(
        AiQuotaUsage.user_id == user.id,
        AiQuotaUsage.date == today,
    )
    usage = db.execute(stmt).scalar_one_or_none()
    used = usage.count if usage else 0
    return {
        "used": used,
        "limit": settings.AI_DAILY_QUOTA,
        "remaining": max(0, settings.AI_DAILY_QUOTA - used),
        "date": today.isoformat(),
    }


def check_and_increment_quota(db: Session, user) -> None:
    """检查配额并递增计数。超限抛 ValueError。"""
    today = date.today()
    stmt = select(AiQuotaUsage).where(
        AiQuotaUsage.user_id == user.id,
        AiQuotaUsage.date == today,
    )
    usage = db.execute(stmt).scalar_one_or_none()
    if usage is None:
        usage = AiQuotaUsage(user_id=user.id, date=today, count=0)
        db.add(usage)
    if usage.count >= settings.AI_DAILY_QUOTA:
        raise ValueError(
            f"今日 AI 调用次数已达上限（{settings.AI_DAILY_QUOTA} 次），请明天再试"
        )
    usage.count += 1
    usage.last_call_at = datetime.now()
    db.commit()


def decrement_quota(db: Session, user) -> None:
    """回退一次配额计数（API 调用失败时调用，避免用户白白损失配额）。

    若 count 已为 0 则不操作（防御性）。
    """
    today = date.today()
    stmt = select(AiQuotaUsage).where(
        AiQuotaUsage.user_id == user.id,
        AiQuotaUsage.date == today,
    )
    usage = db.execute(stmt).scalar_one_or_none()
    if usage is None or usage.count <= 0:
        return
    usage.count -= 1
    db.commit()


# ---------------------------------------------------------------------------
# 上下文消息构建
# ---------------------------------------------------------------------------

def build_messages(
    db: Session, session: ChatSession, user, context: ChatContext | None = None
) -> list[dict]:
    """构建发送给 DeepSeek API 的 messages 数组。

    结构：[system_prompt] + 最近 N 条历史消息（含刚保存的 user 消息）
    """
    system_prompt = build_system_prompt(user, context)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # 查询最近 N 条历史消息（正序，含最新 user 消息）
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(settings.AI_CONTEXT_WINDOW)
    )
    history = list(db.execute(stmt).scalars().all())
    history.reverse()  # 反转为正序

    for msg in history:
        # 仅注入 user 和 assistant 消息（system 一般不持久化）
        if msg.role in ("user", "assistant"):
            messages.append({"role": msg.role, "content": msg.content})

    return messages


# ---------------------------------------------------------------------------
# 流式生成
# ---------------------------------------------------------------------------

async def stream_chat(
    db: Session,
    user,
    session: ChatSession,
    message: str,
    context: ChatContext | None = None,
    is_new_session: bool = False,
) -> AsyncGenerator[str, None]:
    """流式对话生成器，yield SSE 格式事件。

    流程：
    1. 校验 API Key 已配置
    2. 配额检查与递增
    3. 保存 user 消息
    4. 首次对话自动生成标题
    5. 构建上下文消息
    6. 选择模型
    7. 调用 DeepSeek API 流式生成
    8. 累积完整响应并保存 assistant 消息
    9. yield done 事件（含 message_id）

    错误处理：
    - API 未配置/配额超限时，若 is_new_session=True 则清理空会话（避免数据库残留）
    - API 调用失败时回退配额（避免用户白白损失配额）

    异常时 yield error 事件。
    """
    # 重新附加 ORM 对象到当前会话（避免异步上下文中 detached）
    session = db.merge(session)
    user = db.merge(user)

    # 1. 校验 API Key
    if not is_ai_configured():
        yield sse_event("error", {"message": "AI 服务未配置，请联系管理员"})
        if is_new_session:
            db.delete(session)
            db.commit()
        return

    # 2. 配额检查
    try:
        check_and_increment_quota(db, user)
    except ValueError as e:
        yield sse_event("error", {"message": str(e)})
        if is_new_session:
            db.delete(session)
            db.commit()
        return

    # 3. 保存 user 消息
    user_msg = ChatMessage(session_id=session.id, role="user", content=message)
    db.add(user_msg)

    # 4. 首次对话自动生成标题（首条消息截断）
    is_first_message = session.title == "新对话"
    if is_first_message:
        title = message.strip()[: settings.AI_SESSION_TITLE_MAXLEN]
        if not title:
            title = "新对话"
        session.title = title

    db.commit()
    db.refresh(user_msg)
    db.refresh(session)

    # 5. 构建上下文
    messages = build_messages(db, session, user, context)

    # 6. 选择模型
    model = select_model(message)

    # 7. 流式调用 DeepSeek API
    full_content = ""
    try:
        client = get_client()
        stream = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                full_content += delta
                yield sse_event("delta", {"content": delta})

        # 8. 保存 assistant 消息
        if full_content:
            assistant_msg = ChatMessage(
                session_id=session.id,
                role="assistant",
                content=full_content,
                model_used=model,
            )
            db.add(assistant_msg)
            db.commit()
            db.refresh(assistant_msg)
            yield sse_event("done", {"message_id": assistant_msg.id, "model": model})
        else:
            # 空响应也回退配额
            try:
                decrement_quota(db, user)
            except Exception:
                logger.exception("Failed to decrement quota for user %s", user.id)
            yield sse_event(
                "error", {"message": "AI 返回了空响应，请重试或换个问题"}
            )

    except Exception as e:
        logger.exception("AI stream chat failed for user %s", user.id)
        # 回退配额（用户没拿到完整回复，不应损失配额）
        try:
            decrement_quota(db, user)
        except Exception:
            logger.exception("Failed to decrement quota for user %s", user.id)
        # 即使失败也保存已生成的部分内容（便于用户回看）
        if full_content:
            try:
                assistant_msg = ChatMessage(
                    session_id=session.id,
                    role="assistant",
                    content=full_content + f"\n\n[生成中断：{str(e)}]",
                    model_used=model,
                )
                db.add(assistant_msg)
                db.commit()
            except Exception:
                logger.exception("Failed to save partial AI response")
        yield sse_event("error", {"message": f"AI 服务调用失败：{str(e)}"})


# ---------------------------------------------------------------------------
# 会话清理
# ---------------------------------------------------------------------------

def cleanup_old_sessions(db: Session, days: int = SESSION_RETENTION_DAYS) -> int:
    """清理超过指定天数的会话及其消息（级联删除）。返回删除条数。"""
    cutoff = datetime.now() - timedelta(days=days)
    stmt = select(ChatSession).where(ChatSession.updated_at < cutoff)
    old_sessions = list(db.execute(stmt).scalars().all())
    count = len(old_sessions)
    for session in old_sessions:
        db.delete(session)
    if count > 0:
        db.commit()
        logger.info("Cleaned up %d old AI chat sessions", count)
    return count
