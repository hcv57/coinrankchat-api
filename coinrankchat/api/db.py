import time
import datetime
from elasticsearch_dsl import connections, DocType, Text, Integer, Date, datetime, Keyword, Float

from . import config

_connection = connections.create_connection(hosts=[config.ELASTIC_HOST], timeout=10, max_retries=20)

while not _connection.ping():
    time.sleep(5)

class ChatUpdate(DocType):
    channel_id = Keyword()
    from_id = Keyword()
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
                ("global_sentiment_average", response.aggregations.global_sentiment_average.value),
                *[(r.key, dict(
                    num_messages=r.doc_count,
                    max_participants=int(r.max_participants.value or 0),
                    distinct_participants=r.distinct_participants.value,
                    sentiment_average=r.sentiment_average.value
                )) for r in b.byDateRange.buckets]
            ]
        )
        for b in response.aggregations.byChannel.buckets
    ]

def load_channel(_id):
    return ChatUpdate.get(_id).to_dict()

def load_message_count_histogram(channel_id):
    response = ChatUpdate.search().from_dict(get_MESSAGE_COUNT_HISTOGRAM_QUERY(channel_id)).execute()
    # return response.to_dict()
    def get_participants(rec):
        try:
            return rec["latestDocs"]["hits"]["hits"][0]["_source"]["participants_count"]
        except:
            return None
    return [dict(
        date=datetime.utcfromtimestamp(x.key/1000).strftime('%b %d'),
        count=x.doc_count,
        participants=get_participants(x.to_dict())
    ) for x in response.aggregations.messages_over_time.buckets]


_setup_database()

SEARCH_QUERY = {
  "query": {
  "bool": {
    "filter": [
      {"range": {"created_at": {"gte": "now-3d"}}},
      {"exists": {"field": "from_id"}}
    ]
  }
},
  "size": 0,
  "aggs": {
    "global_sentiment_average": {
      "avg": {
        "field": "sentimentPolarity"
      }
    },
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
            "distinct_participants":{
              "cardinality": {
                "field": "from_id"
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

get_MESSAGE_COUNT_HISTOGRAM_QUERY = lambda channel_id: {
  "query": {
  "bool": {
    "filter": [
      {"range": {"created_at": {"gte": "now-30d"}}},
      {"term":{"channel_id": channel_id}}
    ]
  }},
    "size": 0,
    "aggs" : {
        "messages_over_time" : {
            "date_histogram" : {
                "field" : "created_at",
                "interval" : "day",
                "format" : "MMM d"
            },
            "aggs": {
              "latestDocs": {
                "top_hits": {
                  "size": 1,
                        "_source": {
                            "includes": [ "participants_count", "price" ]
                        },
                  "sort": [{"created_at": {"order": "desc"}}]
                }
              }
            }
        }
    }
}