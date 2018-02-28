import time
from functools import reduce
from elasticsearch_dsl import connections, DocType, Text, Integer, Date, datetime, Keyword, Float

from . import config

_connection = connections.create_connection(hosts=[config.ELASTIC_HOST], timeout=10, max_retries=20)

while not _connection.ping():
    time.sleep(5)

class ChatUpdate(DocType):
    channel_id = Keyword()
    title = Text()
    about = Text()
    pinnedMessage = Text()
    sentimentPolarity = Float()
    sentimentSubjectivity = Float()
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
    return [
        dict(
            [
                ("_id", b.latestDocs.hits.hits[0]['_id']),
                ("channel_id", b.key),
                ("title",  b.latestDocs.hits.hits[0]['_source'].get('title')),
                *[(r.key, dict(
                    num_messages=r.doc_count,
                    max_participants=int(r.max_participants.value or 0),
                    sentiment_average=r.sentiment_average.value
                )) for r in b.byDateRange.buckets]
            ]
        )
        for b in response.aggregations.byChannel.buckets
    ]

def load_channel(_id):
    return ChatUpdate.get(_id).to_dict()

_setup_database()

SEARCH_QUERY = {
  "query": {
  "constant_score": {
    "filter": {
      "range": {
        "created_at": {
          "gte": "now-3d"
        }
      }
    }
  }
},
  "size": 0,
  "aggs": {
    "byChannel": {
      "terms": {
        "field": "channel_id",
        "size": 9999
      }
      , "aggs": {
        "latestDocs": {
          "top_hits": {
            "size": 1,
            "sort": [{"created_at": {"order": "desc"}}]
          }
        },
        "byDateRange": {
          "date_range": {
            "field": "created_at",
            "ranges": [
              {
                "from": "now-1d",
                "key": "today"
              },
              {
                "from": "now-2d",
                "to": "now-1d",
                "key": "yesterday"
              },
              {
                "to": "now-2d",
                "key": "before_yesterday"
              }
            ]
          }, "aggs": {
            "max_participants": {
              "max": {
                "field": "participants_count"
              }
            },
            "sentiment_average":{
              "avg": {
                "field": "sentimentPolarity"
              }
            }
          }
        }
      }
      }
    }
  }

