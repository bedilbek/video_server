import json
import logging
import os.path
from uuid import uuid4, UUID

import psycopg2
import tornado.escape
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from dotenv import dotenv_values
from requests import post

env = dotenv_values()

connection = psycopg2.connect(
    dbname=env['DB_NAME'],
    user=env['DB_USER'],
    password=env['DB_PASSWD'],
    host=env['DB_HOST'],
    port=env['DB_PORT']
)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", IndexHandler),
            (r"/uploader", UploadHandler),
            (r"/analyzer/", AnalyzeHandler),
            (r"/streamer", StreamHandler),
            (r"/socket_stream", SocketStreamHandler)
        ]

        settings = dict(
            cookie_secret=env['COOKIE_SECRET'],
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=False,
            autoescape=None,
            debug=True
        )
        tornado.web.Application.__init__(self, handlers, **settings)


class SocketHandler(tornado.websocket.WebSocketHandler):

    def open(self):
        logging.info('new connection')

    def on_message(self, message):
        # image = Image.open(StringIO.StringIO(message))
        # cv_image = numpy.array(image)
        # self.process(cv_image)
        pass

    def on_close(self):
        logging.info('connection closed')

    def process(self, cv_image):
        pass


class StreamHandler(tornado.web.RequestHandler):
    def get(self):
        self.render('streamer.html')


class IndexHandler(tornado.web.RequestHandler):
    def get(self):
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM video WHERE id='5ee438ef-cac1-43d6-8cab-c0783fb4062a';")
        connection.commit()
        video = cursor.fetchone()
        cursor.close()
        self.render('index.html', video_path=video[1], emotion=video[2], gaze=video[3])

    def post(self):
        name = self.get_argument("label", None)
        if not name:
            logging.error("No label, bailing out")
            return
        logging.info("Got label %s" % name)
        logging.info("Setting secure cookie %s" % name)
        self.set_secure_cookie('label', name)
        self.redirect("/")


class UploadHandler(tornado.web.RequestHandler):
    def get(self):
        self.render("uploader.html")

    def post(self):
        req_file = self.request.files['video'][0]
        print("file name: ", req_file['filename'])
        file_extn = os.path.splitext(req_file['filename'])[1]
        if file_extn not in ['.mp4', '.avi', '.MP4', '.AVI', '.aVi', '.Mp4', '.mP4', '.AvI', '.AVi']:
            self.finish(
                'File Extension is not recognized, Please reupload with one of the following extenstions: .mp4, .avi')
        file_id = uuid4()
        filename = str(file_id) + file_extn
        file_path = os.path.join(env['VIDEO_SERVER_UPLOAD_PATH'], filename)
        with open(os.getcwd() + file_path, 'wb') as f:
            f.write(req_file['body'])
            f.flush()
            f.close()
        cursor = connection.cursor()
        cursor.execute("INSERT INTO video VALUES ('{0}', '{1}', null, null );".format(str(file_id), file_path))
        connection.commit()
        cursor.close()
        print("emotion")
        emotion_response = post(env['SERVER_ANALYZER_IP'] + '/emotion/', json={'video_id': str(file_id), 'video_path': file_path}, headers={'Content-Type': 'application/json'})
        print("gaze")
        gaze_response = post(env['SERVER_ANALYZER_IP'] + '/gaze/', json={'video_id': str(file_id), 'video_path': file_path}, headers={'Content-Type': 'application/json'})
        print("finish")
        self.render("file_uploaded.html", video_id=str(file_id))
        print("render")


class AnalyzeHandler(tornado.web.RequestHandler):
    def get(self):
        video_id = self.get_arguments('video_id')
        if len(video_id) == 0 or len(video_id) > 1:
            self.finish("Sorry, this page could not be processed")
            return
        try:
            uuid = UUID(video_id[0], version=4)
        except:
            self.finish("Enter a valid video_id")
            return
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM video WHERE id='{0}'".format(video_id[0]))
        connection.commit()
        video = cursor.fetchone()
        if video is None:
            self.finish("Sorry, There is no such entity")
            cursor.close()
            return
        cursor.close()
        if video[2] is None or video[3] is None:
            self.render("analyzed_error.html")
            return
        self.render('index.html', video_path=video[1], emotion=video[2], gaze=video[3])


class SocketStreamHandler(SocketHandler):
    def process(self, cv_image):
        obj = dict(text="HarvesterHandler Hello World")
        self.write_message(json.dumps(obj))


def main():
    if not os.path.exists(os.getcwd() + env['VIDEO_SERVER_UPLOAD_PATH']):
        os.makedirs(os.getcwd() + env['VIDEO_SERVER_UPLOAD_PATH'])
    tornado.options.parse_command_line()
    logging.info("Server is preparing for running")
    app = Application()
    app.listen(env['VIDEO_SERVER_PORT'])
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
