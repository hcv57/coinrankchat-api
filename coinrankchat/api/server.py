import falcon
import json
import datetime

from . import db


class Groups():

    def on_get(self, _req, resp):
        doc = db.load_all_channels()
        resp.body = json.dumps(doc, ensure_ascii=False, indent=" ")


class Group():

    def datetime_handler(self, d):
        if isinstance(d, datetime.datetime):
            return d.isoformat()

    def on_get(self, _req, resp, _id):
        print("Looking up %s" % _id)
        doc = db.load_channel(_id)
        resp.body = json.dumps(doc, ensure_ascii=False, indent=" ", default=self.datetime_handler)


class ChannelStats():

    def on_get(self, _req, resp, channel_id):
        doc = db.load_message_count_histogram(channel_id)
        resp.body = json.dumps(doc, ensure_ascii=False, indent=" ")


api = app = falcon.API()
api.add_route('/api/groups', Groups())
app.add_route('/api/group/{_id}', Group())
app.add_route('/api/channel/{channel_id}/stats', ChannelStats())