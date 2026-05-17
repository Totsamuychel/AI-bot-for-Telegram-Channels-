from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, Text, String, Integer, Boolean, DateTime
from datetime import datetime
from .config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class BotSetting(Base):
    __tablename__ = "bot_settings"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String, nullable=True, default="llama3.2")
    schedule_interval: Mapped[int] = mapped_column(Integer, nullable=True, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    llm_source: Mapped[str] = mapped_column(String, nullable=True, default="ollama")
    api_key: Mapped[str] = mapped_column(String, nullable=True)
    api_base_url: Mapped[str] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(String, nullable=True, default="RU")
    post_style: Mapped[str] = mapped_column(String, nullable=True, default="informative")
    image_source: Mapped[str] = mapped_column(String, nullable=True, default="none")
    extra_admins: Mapped[str] = mapped_column(Text, nullable=True, default="[]")
    target_channels: Mapped[str] = mapped_column(Text, nullable=True, default="[]")
    auto_post: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    auto_approve_news: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # "interval" — fixed minutes between posts; "weekly" — JSON schedule by day
    schedule_mode: Mapped[str] = mapped_column(String, nullable=True, default="interval")
    # JSON: {"mon": ["09:00", "18:00"], "sat": ["12:00"], ...}
    post_schedule: Mapped[str] = mapped_column(Text, nullable=True, default="{}")


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    # pending -> approved -> pending_review -> ready_to_post -> posted | rejected
    generated_text: Mapped[str] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)


class SettingsPreset(Base):
    __tablename__ = "settings_presets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=True)
    model: Mapped[str] = mapped_column(String, default="llama3.2")
    schedule_interval: Mapped[int] = mapped_column(Integer, default=60)
    llm_source: Mapped[str] = mapped_column(String, default="ollama")
    api_key: Mapped[str] = mapped_column(String, nullable=True)
    api_base_url: Mapped[str] = mapped_column(String, nullable=True)
    language: Mapped[str] = mapped_column(String, default="RU")
    post_style: Mapped[str] = mapped_column(String, default="informative")
    image_source: Mapped[str] = mapped_column(String, default="none")
    extra_admins: Mapped[str] = mapped_column(Text, nullable=True, default="[]")
    target_channels: Mapped[str] = mapped_column(Text, nullable=True, default="[]")
    schedule_mode: Mapped[str] = mapped_column(String, default="interval")
    post_schedule: Mapped[str] = mapped_column(Text, nullable=True, default="{}")


class Worker(Base):
    """Remote posting worker on a separate machine."""
    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    url: Mapped[str] = mapped_column(String, nullable=False)   # e.g. http://192.168.1.10:8010
    token: Mapped[str] = mapped_column(String, nullable=False)  # Telegram bot token for this worker
    # JSON list of channel IDs this worker handles, e.g. [-100123, -100456]
    channels: Mapped[str] = mapped_column(Text, nullable=True, default="[]")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at = mapped_column(DateTime, default=datetime.utcnow)


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_bot_setting(session: AsyncSession):
    from sqlalchemy import select
    result = await session.execute(select(BotSetting).limit(1))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = BotSetting()
        session.add(setting)
    return setting
