from sqlalchemy.engine import URL
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

import pandas as pd

from . import db


def read_dataframe(url: URL, limit: int = None):
    engine = create_engine(url)
    with Session(engine) as s:
        query_read = s.query(db.News)
        if limit is not None:
            query_read = query_read.limit(limit)
        # Request news
        news = pd.read_sql(query_read.statement, s.connection())
        # Request tags
        news_tags = pd.read_sql(
            s.query(db.NewsTags).filter(db.NewsTags.news_id.in_(news['id'])).statement,
            s.connection())
        tags = pd.read_sql(
            s.query(db.Tag).filter(db.Tag.id.in_(map(int, news_tags['tag_id'].unique()))).statement,
            s.connection())
        # Merge tags
        news_tags = pd.merge(
            news_tags, tags, how='left', left_on='tag_id', right_on='id', copy=False
        ).groupby('news_id')['name'].apply(list)
        news = pd.merge(
            news, news_tags, how='left', left_on='id', right_on='news_id', copy=False
        )
        news.rename(columns={"name": "tags", "type_name": "type"}, inplace=True)

        for subt in db.News.__subclasses__():
            right = pd.read_sql(
                s.query(subt).with_entities(
                    *(set(subt.__mapper__.columns) - set(db.News.__mapper__.columns))
                ).filter(subt.id.in_(news['id'])).statement,
                s.connection())
            news = pd.merge(news, right, how='left', left_on='id', right_on='id', copy=False)
        # Postprocess
        water_null = news['water_x'].isnull()
        news.loc[water_null, ['water_x']] = news['water_y']
        news.drop(columns='water_y', inplace=True)
        news.rename(columns={"water_x": "water"}, inplace=True)
    # news.set_index('id', inplace=True)
    return news.convert_dtypes()
