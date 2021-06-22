"""
SQLAlchemy database mappings
"""
from typing import List

from sqlalchemy.event import listens_for
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.engine import Connection
from sqlalchemy import MetaData, Table, Column, ForeignKey, Integer, String, Text, DateTime

__all__ = ["Base",
           "News",
           "Fire", "Traffic", "Rescue", "Drown", "Flood",
           "Category", "Tag", "Type",
           "NewsCategories", "NewsTags",
           "ExistingNews"]

Base = declarative_base()


class News(Base):
    __tablename__ = "news"

    __table_args__ = {
        "comment": "General news table with all data, directly retrieved from HTML pages and discriminator type column"
    }

    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    title = Column(Text)
    text = Column(Text)
    image = Column(Text)
    type_name = Column(String(25), ForeignKey("types.name"))
    type = relationship("Type", back_populates="news")

    region = Column(String(50))
    city = Column(String(50))
    # street = Column(String(50))
    injuries = Column(Integer)
    # lethal = Column(Integer)
    n_staff = Column(Integer)
    n_tech = Column(Integer)

    categories_assoc = relationship("NewsCategories",
                                    back_populates="news",
                                    order_by="NewsCategories.priority",
                                    cascade="all, delete-orphan")
    categories = association_proxy("categories_assoc", "category", creator=lambda x: NewsCategories(category=x))
    category = relationship("Category",
                            primaryjoin="and_(NewsCategories.news_id == News.id, NewsCategories.priority == 0)",
                            secondary="news__categories",
                            uselist=False,
                            viewonly=True)
    tags_assoc = relationship("NewsTags",
                              back_populates="news",
                              order_by="NewsTags.priority",
                              cascade="all, delete-orphan")
    tags = association_proxy("tags_assoc", "tag", creator=lambda x: NewsTags(tag=x))

    __mapper_args__ = {
        "polymorphic_on": "type_name",
        "polymorphic_identity": "news"
    }

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, title=\"{self.title}\")"


class Fire(News):
    __tablename__ = "news_fire"

    id = Column(Integer, ForeignKey(News.id), primary_key=True)
    area = Column(Integer)

    __mapper_args__ = {"polymorphic_identity": "fire"}


class Traffic(News):
    __tablename__ = "news_traffic"

    id = Column(Integer, ForeignKey(News.id), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": "traffic"}


class Rescue(News):
    __tablename__ = "news_rescue"

    id = Column(Integer, ForeignKey(News.id), primary_key=True)

    __mapper_args__ = {"polymorphic_identity": "rescue"}


class Drown(News):
    __tablename__ = "news_drown"

    id = Column(Integer, ForeignKey(News.id), primary_key=True)
    water = Column(String(50))

    __mapper_args__ = {"polymorphic_identity": "drown"}


class Flood(News):
    __tablename__ = "news_flood"

    id = Column(Integer, ForeignKey(News.id), primary_key=True)
    water = Column(String(50))

    __mapper_args__ = {"polymorphic_identity": "flood"}


class ExistingNews(Base):
    __tablename__ = "__existing_news"
    __table_args__ = {
        "comment": "Service table, news that were met during parsing of pages, but not parsed individually yet."
    }

    id = Column(Integer, primary_key=True)
    news = relationship("News",
                        foreign_keys=id,
                        primaryjoin=News.id == id,
                        uselist=False,
                        viewonly=True)


class Type(Base):
    __tablename__ = "types"

    name = Column(String(25), primary_key=True)
    full_name = Column(String(50))
    news = relationship(News)

    def __repr__(self):
        return f"{self.__class__.__name__}(name=\"{self.name}\", full_name=\"{self.full_name}\")"


class Category(Base):
    __tablename__ = "categories"

    name = Column(String(25), primary_key=True)
    full_name = Column(String(50))
    news_assoc = relationship("NewsCategories", back_populates="category")
    news = association_proxy("news_assoc", "news", creator=lambda x: NewsCategories(news=x))

    # news = relationship(News, secondary="news__categories", back_populates="categories")

    def __repr__(self):
        return f"{self.__class__.__name__}(name=\"{self.name}\", full_name=\"{self.full_name}\")"


class NewsCategories(Base):
    __tablename__ = "news__categories"

    news_id = Column(Integer, ForeignKey(News.id, ondelete="CASCADE"), primary_key=True)
    news = relationship(News, back_populates="categories_assoc")
    category_name = Column(String(25), ForeignKey(Category.name, ondelete="CASCADE"), primary_key=True)
    category = relationship(Category, back_populates="news_assoc")
    priority = Column(Integer)

    def __repr__(self):
        return f"{self.__class__.__name__}" \
               f"(news_id={self.news_id}, category=\"{self.category_name}\", priority={self.priority})"


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True)
    name = Column(Text)
    news_assoc = relationship("NewsTags", back_populates="tag")
    news = association_proxy("news_assoc", "news", creator=lambda x: NewsTags(news=x))

    # news = relationship(News, secondary="news__tags", back_populates="tags")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"


class NewsTags(Base):
    __tablename__ = "news__tags"

    news_id = Column(Integer, ForeignKey(News.id, ondelete="CASCADE"), primary_key=True)
    news = relationship(News, back_populates="tags_assoc")
    tag_id = Column(Integer, ForeignKey(Tag.id, ondelete="CASCADE"), primary_key=True)
    tag = relationship(Tag, back_populates="news_assoc")
    priority = Column(Integer)

    def __repr__(self):
        return f"{self.__class__.__name__}(news_id={self.news_id}, tag_id={self.tag_id}, priority={self.priority})"


@listens_for(Base.metadata, "after_create")
def create_types(metadata: MetaData, con: Connection, tables: List[Table] = (), **kwargs):
    type_names = set()
    for mapper in Base.registry.mappers:
        if (type_name := mapper.polymorphic_identity) is not None:
            type_names.add(type_name)
    for table in tables:
        if table.name == Type.__tablename__:
            with con.begin():
                for type_name in type_names:
                    con.execute(table.insert(), {"name": type_name})
            break
