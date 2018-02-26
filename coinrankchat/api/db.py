import time
from elasticsearch_dsl import connections, DocType, Text, Integer, Date, datetime, Keyword

from . import config

_connection = connections.create_connection(hosts=[config.ELASTIC_HOST], timeout=10, max_retries=20)

while not _connection.ping():
    time.sleep(5)

class ChatUpdate(DocType):
    channel_id = Keyword()
    title = Text()
    about = Text()
    username = Keyword()
    participants_count = Integer()
    created_at = Date()

    class Meta:
        index = 'chatupdates'

    def save(self, **kwargs):
        self.created_at = datetime.utcnow()
        return super().save(**kwargs)

def _setup_database():
    ChatUpdate.init()

def load_all_channels():
    response = ChatUpdate.search().from_dict(SEARCH_QUERY).execute()
    buckets = response.aggregations.group.buckets
    return [
        dict(
            [
                ("_id", b.group_docs.hits.hits[0]['_id']),
                ("rank", i+1),
                ("channel_id", b.key),
                ("title",  b.group_docs.hits.hits[0]['_source'].get('title')),
                ("about",  b.group_docs.hits.hits[0]['_source'].get('about')),
                ("username",  b.group_docs.hits.hits[0]['_source'].get('username')),
                ("participants_count", b.group_docs.hits.hits[0]['_source'].get('participants_count')),
                *[(r.key, r.doc_count) for r in b.range.buckets]
            ]
        )
        for (i, b) in enumerate(buckets) if b.group_docs.hits.hits[0]['_source'].get('username')
    ]

def load_channel(_id):
    return ChatUpdate.get(_id).to_dict()

_setup_database()

SEARCH_QUERY = {"query": {
  "constant_score": {
    "filter": {
      "range": {
        "created_at": {
          "gte": "now-2d"
        }
      }
    }
  }
},"size": 0,
  "aggs": {
  "group": {
    "terms": {
      "field": "channel_id",
      "size": 1000
    },
    "aggs": {
      "group_docs": {
        "top_hits": {
          "size": 1,
          "sort": [{"created_at": {"order": "desc"}}]
        }
      },
      "range":{
        "date_range": {
          "field": "created_at",
          "ranges": [
              {
                  "key": "messages_1h",
                  "from": "now-1h"
              },
              {
                  "key": "messages_prev_1h",
                  "from": "now-2h",
                  "to": "now-1h"
              },
              {
                  "key": "messages_24h",
                  "from": "now-1d"
              },
              {
                  "key": "messages_prev_24h",
                  "from": "now-2d",
                  "to": "now-1d"
              },
          ]
        }
      }
    }
  }
}}
