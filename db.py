"""
SQLAlchemy database mappings
"""
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime

__all__ = ["Base", "News", "Categories", "Tags", "Types", "NewsCategories", "NewsTags"]

Base = declarative_base()


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    date = Column(DateTime)
    text = Column(Text)
    type_name = Column(String(25), ForeignKey("types.name"))
    type = relationship("Types", back_populates="news")

    categories = relationship("Categories",
                              secondary="news_categories",
                              order_by="news_categories.priority",
                              back_populates="news")
    category = relationship("Categories",
                            primaryjoin="and_(news_categories.news_id == news.id, news_categories.priority == 0)",
                            uselist=False,
                            secondary="news_categories")
    tags = relationship("Tags",
                        secondary="news_tags",
                        order_by="news_tags.priority",
                        back_populates="news")

    __mapper_args__ = {
        "polymorphic_on": "type_name"
    }


class ExistingNews(Base):
    __tablename__ = "__existing_news"
    __table_args__ = {
        "comment": "Service table, news that were met during parsing of pages, but not parsed individually yet."
    }

    id = Column(Integer, ForeignKey("news.id"), primary_key=True)
    news = relationship("News")


class ParsedNews(Base):
    __tablename__ = "__parsed_news"
    __table_args__ = {"comment": "Service table, news that were fetched and parsed, but not processed yet."}

    id = Column(Integer, ForeignKey("news.id"), primary_key=True)
    news = relationship("News")


class Types(Base):
    __tablename__ = "types"

    name = Column(String(25), primary_key=True)
    full_name = Column(String(50))
    news = relationship("News")


class Categories(Base):
    __tablename__ = "categories"

    name = Column(String(25), primary_key=True)
    full_name = Column(String(50))
    news = relationship("News", secondary="news_categories", back_populates="categories")


class NewsCategories(Base):
    __tablename__ = "news_categories"

    news_id = Column(Integer, ForeignKey("news.id"), primary_key=True)
    category = Column(String(25), ForeignKey("categories.name"), primary_key=True)
    priority = Column(Integer)


class Tags(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(String(25))
    news = relationship("News", secondary="news_tags", back_populates="tags")


class NewsTags(Base):
    __tablename__ = "news_tags"

    news_id = Column(Integer, ForeignKey("news.id"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id"), primary_key=True)
    priority = Column(Integer)
