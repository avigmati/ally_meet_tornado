import tornado
import tornado.ioloop
import tornado.web
import os
import uuid

_UPLOAD_PATH = './upload'


class UploadForm(tornado.web.RequestHandler):
    def get(self):
        self.render("upload_form.html")

class Upload(tornado.web.RequestHandler):
    def post(self):
        filename = '{}_{}'.format(uuid.uuid4(), self.request.files['fileobj'][0]['filename'])
        self._write_file(self.request.files['fileobj'][0], filename)
        self.write("file " + self.request.files['fileobj'][0]['filename'] + " is uploaded!")
        self.finish()

    def _write_file(self, file, filename):
        output_file = open(os.path.join(_UPLOAD_PATH, filename), 'wb')
        output_file.write(file.body)
        output_file.close()


app = tornado.web.Application([
    (r"/", UploadForm),
    (r"/upload", Upload),
], debug=True)

def run():
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    run()