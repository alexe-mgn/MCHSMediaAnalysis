"""
SQLAlchemy database mappings
"""
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.ext.associationproxy import association_proxy
# from sqlalchemy.ext.automap import automap_base
from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime

__all__ = ["Base",
           "News", "Category", "Tag", "Type",
           "NewsCategories", "NewsTags",
           "ExistingNews"]

Base = declarative_base()


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    date = Column(DateTime)
    text = Column(Text)
    image = Column(Text)
    type_name = Column(String(25), ForeignKey("types.name"))
    type = relationship("Type", back_populates="news")

    categories_assoc = relationship("NewsCategories",
                                    back_populates="news",
                                    order_by="NewsCategories.priority",
                                    cascade="all, delete-orphan")
    categories = association_proxy("categories_assoc", "category", creator=lambda x: NewsCategories(category=x))
    # categories = relationship("Category",
    #                           secondary="news_categories",
    #                           back_populates="news",
    #                           order_by="NewsCategories.priority")
    category = relationship("Category",
                            primaryjoin="and_(NewsCategories.news_id == News.id, NewsCategories.priority == 0)",
                            secondary="news_categories",
                            uselist=False,
                            viewonly=True)
    tags_assoc = relationship("NewsTags",
                              back_populates="news",
                              order_by="NewsTags.priority",
                              cascade="all, delete-orphan")
    tags = association_proxy("tags_assoc", "tag", creator=lambda x: NewsTags(tag=x))
    # tags = relationship("Tag",
    #                     secondary="news_tags",
    #                     back_populates="news",
    #                     order_by="NewsTags.priority")

    __mapper_args__ = {
        "polymorphic_on": "type_name"
    }

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, title=\"{self.title}\")"


class ExistingNews(Base):
    __tablename__ = "__existing_news"
    __table_args__ = {
        "comment": "Service table, news that were met during parsing of pages, but not parsed individually yet."
    }

    id = Column(Integer, ForeignKey("news.id"), primary_key=True)
    news = relationship("News")


# class ParsedNews(Base):
#     __tablename__ = "__parsed_news"
#     __table_args__ = {"comment": "Service table, news that were fetched and parsed, but not processed yet."}
#
#     id = Column(Integer, ForeignKey("news.id"), primary_key=True)
#     news = relationship("News")


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
    # news = relationship(News, secondary="news_categories", back_populates="categories")

    def __repr__(self):
        return f"{self.__class__.__name__}(name=\"{self.name}\", full_name=\"{self.full_name}\")"


class NewsCategories(Base):
    __tablename__ = "news_categories"

    news_id = Column(Integer, ForeignKey(News.id), primary_key=True)
    news = relationship(News, back_populates="categories_assoc")
    category_name = Column(String(25), ForeignKey(Category.name), primary_key=True)
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
    # news = relationship(News, secondary="news_tags", back_populates="tags")

    def __repr__(self):
        return f"{self.__class__.__name__}(id={self.id}, name={self.name})"


class NewsTags(Base):
    __tablename__ = "news_tags"

    news_id = Column(Integer, ForeignKey(News.id), primary_key=True)
    news = relationship(News, back_populates="tags_assoc")
    tag_id = Column(Integer, ForeignKey(Tag.id), primary_key=True)
    tag = relationship(Tag, back_populates="news_assoc")
    priority = Column(Integer)

    def __repr__(self):
        return f"{self.__class__.__name__}(news_id={self.news_id}, tag_id={self.tag_id}, priority={self.priority})"
